import os
from pathlib import Path

import torch
from torch import nn as nn
from transformers import BertConfig, BertModel

from readability_classifier.models.base_model import BaseModel
from readability_classifier.utils.config import SemanticInput
from readability_classifier.utils.utils import load_yaml_file

CURR_DIR = Path(os.path.dirname(os.path.relpath(__file__)))
DEFAULT_SAVE_PATH = CURR_DIR / Path("../../../models/")
CONFIGS_PATH = CURR_DIR / Path("../../res/models/")


# TODO: Try out: BertForPreTraining


class OwnBertConfig(BertConfig):
    """
    Configuration class to store the configuration of a `BertEmbedding`.
    Same as in TowardsBert paper.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vocab_size = kwargs.get("vocab_size", 30000)  # 28996
        self.type_vocab_size = kwargs.get("type_vocab_size", 300)
        self.hidden_size = kwargs.get("hidden_size", 768)
        self.num_hidden_layers = kwargs.get("num_hidden_layers", 12)
        self.num_attention_heads = kwargs.get("num_attention_heads", 12)
        self.intermediate_size = kwargs.get("intermediate_size", 3072)
        self.hidden_activation = kwargs.get("hidden_activation", "gelu")
        self.hidden_dropout_rate = kwargs.get("hidden_dropout_rate", 0.1)
        self.attention_dropout_rate = kwargs.get("attention_dropout_rate", 0.1)
        self.max_position_embeddings = kwargs.get("max_position_embeddings", 200)  # 512
        self.max_sequence_length = kwargs.get("max_sequence_length", 100)

    @classmethod
    def build_config(cls) -> "OwnBertConfig":
        """
        Build the model from a config.
        :return: Returns the model.
        """
        return cls(**cls._get_config())

    @classmethod
    def _get_config(cls) -> dict[str, ...]:
        """
        Get the config hyperparams.
        :return: The hyperparams.
        """
        return load_yaml_file(CONFIGS_PATH / f"{cls.__name__.lower()}.yaml")


# TODO: In code: token_type_embeddings instead of segment_embeddings
class OwnBertEmbedding(BaseModel):
    """
    A Bert embedding layer similar to the one used in the TowardsBert paper.
    The embedding weights are trained from scratch!
    """

    def __init__(self, config: OwnBertConfig) -> None:
        super().__init__()

        # Specify device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load the model
        self.model_name = "bert-base-cased"
        self.model = BertModel.from_pretrained(self.model_name)

        # TODO: Try without copying?
        # Copy the token embedding layer from the model
        self.token_embedding = self.model.embeddings.word_embeddings

        # Initialize segment and position embedding layers
        self.type_vocab_size = config.type_vocab_size
        # self.segment_embedding = nn.Embedding(
        #     config.type_vocab_size, config.hidden_size
        # )
        self.position_embedding = nn.Embedding(
            config.max_position_embeddings, config.hidden_size
        )

        self.layer_norm = nn.LayerNorm(config.hidden_size, eps=1e-12)
        self.dropout = nn.Dropout(config.hidden_dropout_rate)
        # self.segment_embedding.weight.data.normal_(mean=0.0, std=0.02)
        self.position_embedding.weight.data.normal_(mean=0.0, std=0.02)

        # Send the embeddings to the GPU
        self.layer_norm.to(self.device)
        self.dropout.to(self.device)
        self.token_embedding.to(self.device)
        # self.segment_embedding.to(self.device)
        self.position_embedding.to(self.device)

    def forward(self, x: SemanticInput) -> torch.Tensor:
        """
        Embed the input using Bert.
        :param x: The input.
        :return:
        """
        input_ids = x.input_ids
        # token_type_ids is unused
        # attention_mask is unused
        segment_ids = x.segment_ids

        batch_size, sequence_length = input_ids.size()

        # Create position ids
        position_ids = torch.arange(sequence_length, dtype=torch.long).unsqueeze(0)
        position_ids = position_ids % self.position_embedding.weight.size(0)
        # position_ids = position_ids.repeat(batch_size, 1)

        # Move input tensors to GPU
        input_ids = input_ids.to(self.device)
        segment_ids = segment_ids.cuda(self.device)
        position_ids = position_ids.cuda(self.device)

        # Get embeddings
        with torch.no_grad():  # Don't train token embeddings
            token_embeddings = self.token_embedding(input_ids)
        # segment_embeddings = self.segment_embedding(segment_ids)
        # position_embeddings = self.position_embedding(position_ids)
        position_embeddings = self.position_embedding(position_ids.to(input_ids.device))

        # Sum all embeddings and apply layer norm and dropout
        embeddings = token_embeddings + position_embeddings  # + segment_embeddings
        embeddings = self.layer_norm(embeddings)
        embeddings = self.dropout(embeddings)

        return embeddings

    @classmethod
    def _build_from_config(cls, params: dict[str, ...], save: Path) -> "BaseModel":
        """
        Build the model from a config.
        :param params: The config.
        :param save: The path to save the model.
        :return: Returns the model.
        """
        return cls(OwnBertConfig(**params))


class OwnSemanticExtractorConfig:
    """
    Configuration class to store the configuration of a `SemanticExtractor`.
    """

    def __init__(self, **kwargs: dict[str, ...]):
        # Must be same as hidden_size in BertConfig
        self.input_size = kwargs.get("input_size", 768)


class OwnSemanticExtractor(BaseModel):
    """
    A semantic extractor model. Also known as BertExtractor.
    The model consists of a Bert embedding layer, a convolutional layer, a max pooling
    layer, another convolutional layer and a BiLSTM layer. Relu is used as the
    activation function.
    The input is a tensor of size (1, 512) and the output is a vector of size 10560.
    """

    def __init__(self, config: OwnSemanticExtractorConfig) -> None:
        """
        Initialize the model.
        """
        super().__init__()

        self.bert_embedding = OwnBertEmbedding(OwnBertConfig.build_config())

        # In paper: kernel size not specified
        self.conv1 = nn.Conv1d(
            in_channels=config.input_size, out_channels=32, kernel_size=5
        )

        # Same as in paper
        self.relu = nn.ReLU()

        # Same as in paper
        self.maxpool1 = nn.MaxPool1d(kernel_size=3)

        # In paper: kernel size not specified
        self.conv2 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=5)

        # In paper: args not specified
        self.bidirectional_lstm = nn.LSTM(32, 32, bidirectional=True, batch_first=True)

    def forward(self, x: SemanticInput) -> torch.Tensor:
        """
        Forward pass of the model.
        :param x: The input of the model.
        :return: The output of the model.
        """
        # Embed the input using Bert
        texture_embedded = self.bert_embedding(x)

        # Permute the tensor to fit the convolutional layer
        texture_embedded = texture_embedded.permute(0, 2, 1)

        # Convolutional layers
        x = self.conv1(texture_embedded)
        x = self.relu(x)
        x = self.maxpool1(x)
        x = self.relu(self.conv2(x))

        # Permute the tensor to fit the LSTM layer
        x = x.permute(0, 2, 1)

        # LSTM layer
        x, _ = self.bidirectional_lstm(x)

        # Flatten the tensor after LSTM
        batch_size, seq_length, channels = x.size()
        x = x.contiguous().view(batch_size, -1)  # Flatten the tensor

        return x

    @classmethod
    def _build_from_config(cls, params: dict[str, ...], save: Path) -> "BaseModel":
        """
        Build the model from a config.
        :param params: The config.
        :param save: The path to save the model.
        :return: Returns the model.
        """
        return cls(OwnSemanticExtractorConfig(**params))
