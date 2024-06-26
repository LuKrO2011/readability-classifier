import keras
import tensorflow as tf
from keras import layers, models, optimizers, regularizers

from src.readability_classifier.keas.legacy_encoders import MAX_LEN

# Default values
DEFAULT_LEARNING_RATE = 0.0015
DEFAULT_LOSS = "binary_crossentropy"
DEFAULT_METRICS = [
    "acc",
    "Recall",
    "Precision",
    "AUC",
    "TruePositives",
    "TrueNegatives",
    "FalseNegatives",
    "FalsePositives",
]


def create_classification_layers(input_layer: tf.Tensor) -> tf.Tensor:
    """
    Create the classification model.
    :param input_layer: The input layer of the model.
    :return: The output layer of the model.
    """
    dense1 = layers.Dense(
        units=64,
        activation="relu",
        kernel_regularizer=regularizers.l2(0.001),
        name="class_dense1",
    )(input_layer)
    drop = layers.Dropout(0.5, name="class_dropout")(dense1)
    dense2 = layers.Dense(units=16, activation="relu", name="class_dense2")(drop)
    return layers.Dense(1, activation="sigmoid", name="class_dense3")(dense2)


def create_structural_extractor(
    input_shape: tuple[int, int] = (50, 305)
) -> tuple[tf.Tensor, tf.Tensor]:
    """
    Create the structural extractor layers.
    :param input_shape: The input shape of the model.
    :return: The input layer and the flattened layer.
    """
    model_input = layers.Input(shape=input_shape, name="struc_input")
    reshaped_input = layers.Reshape((*input_shape, 1), name="struc_reshape")(
        model_input
    )

    conv1 = layers.Conv2D(
        filters=32, kernel_size=3, activation="relu", name="struc_conv1"
    )(reshaped_input)
    pool1 = layers.MaxPooling2D(pool_size=2, strides=2, name="struc_pool1")(conv1)

    conv2 = layers.Conv2D(
        filters=32, kernel_size=3, activation="relu", name="struc_conv2"
    )(pool1)
    pool2 = layers.MaxPooling2D(pool_size=2, strides=2, name="struc_pool2")(conv2)

    conv3 = layers.Conv2D(
        filters=64, kernel_size=3, activation="relu", name="struc_conv3"
    )(pool2)
    pool3 = layers.MaxPooling2D(pool_size=3, strides=3, name="struc_pool3")(conv3)

    flattened = layers.Flatten(name="struc_flatten")(pool3)
    return model_input, flattened


def create_structural_model(
    learning_rate: float = DEFAULT_LEARNING_RATE,
) -> keras.Model:
    """
    Create the structural model for the matrix encoding.
    :return: The model.
    """

    structure_input, structure_flatten = create_structural_extractor()
    classification_output = create_classification_layers(structure_flatten)

    model = models.Model(structure_input, classification_output)

    rms = optimizers.RMSprop(learning_rate=learning_rate)

    model.compile(
        optimizer=rms,
        loss=DEFAULT_LOSS,
        metrics=DEFAULT_METRICS,
    )

    return model


def create_semantic_extractor(
    input_shape: tuple[int, int] = (MAX_LEN,)
) -> tuple[tf.Tensor, tf.Tensor, tf.Tensor]:
    """
    Create the semantic extractor layers.
    :param input_shape: The input shape of the model.
    :return: The input layer, the token embedding layer, and the segment embedding layer
    """
    token_input = layers.Input(shape=input_shape, name="seman_input_token")
    segment_input = layers.Input(shape=input_shape, name="seman_input_segment")

    embedding = BertEmbedding(
        config=BertConfig(max_sequence_length=MAX_LEN, name="seman_bert")
    )([token_input, segment_input])

    conv1 = layers.Conv1D(32, 5, activation="relu", name="seman_conv1")(embedding)
    pool1 = layers.MaxPooling1D(3, name="seman_pool1")(conv1)

    conv2 = layers.Conv1D(32, 5, activation="relu", name="seman_conv2")(pool1)

    gru = layers.Bidirectional(layers.LSTM(32, name="seman_lstm"), name="seman_gru")(
        conv2
    )

    return token_input, segment_input, gru


def create_semantic_model(learning_rate: float = DEFAULT_LEARNING_RATE) -> keras.Model:
    """
    Create the semantic model for the bert encoding.
    :param learning_rate: The learning rate of the model.
    :return: The model.
    """
    token_input, segment_input, gru = create_semantic_extractor()
    classification_output = create_classification_layers(gru)

    model = models.Model([token_input, segment_input], classification_output)

    rms = optimizers.RMSprop(learning_rate=learning_rate)

    model.compile(
        optimizer=rms,
        loss=DEFAULT_LOSS,
        metrics=DEFAULT_METRICS,
    )
    return model


def create_visual_extractor(
    input_shape: tuple[int, int, int] = (128, 128, 3)
) -> tuple[tf.Tensor, tf.Tensor]:
    """
    Create the visual extractor layers for the image encoding.
    :param input_shape: The input shape of the model.
    :return: The input layer and the flattened layer.
    """
    model_input = layers.Input(shape=input_shape, name="vis_input")

    conv1 = layers.Conv2D(
        filters=32, kernel_size=3, padding="same", activation="relu", name="vis_conv1"
    )(model_input)
    pool1 = layers.MaxPooling2D(pool_size=2, strides=2, name="vis_pool1")(conv1)

    conv2 = layers.Conv2D(
        filters=32, kernel_size=3, padding="same", activation="relu", name="vis_conv2"
    )(pool1)
    pool2 = layers.MaxPooling2D(pool_size=2, strides=2, name="vis_pool2")(conv2)

    conv3 = layers.Conv2D(
        filters=64, kernel_size=3, padding="same", activation="relu", name="vis_conv3"
    )(pool2)
    pool3 = layers.MaxPooling2D(pool_size=2, strides=2, name="vis_pool3")(conv3)

    flattened = layers.Flatten(name="vis_flatten")(pool3)
    return model_input, flattened


def create_visual_model(learning_rate: float = DEFAULT_LEARNING_RATE) -> keras.Model:
    """
    Create the visual model for the image encoding.
    :param learning_rate: The learning rate of the model.
    :return: The model.
    """
    image_input, image_flatten = create_visual_extractor()
    classification_output = create_classification_layers(image_flatten)

    model = models.Model(image_input, classification_output)

    rms = optimizers.RMSprop(learning_rate=learning_rate)

    model.compile(
        optimizer=rms,
        loss=DEFAULT_LOSS,
        metrics=DEFAULT_METRICS,
    )
    return model


def create_towards_model(learning_rate: float = DEFAULT_LEARNING_RATE) -> keras.Model:
    """
    Create the VST model.
    :return: The model.
    """
    structure_input, structure_flatten = create_structural_extractor()
    token_input, segment_input, gru = create_semantic_extractor()
    image_input, image_flatten = create_visual_extractor()

    concatenated = layers.concatenate([structure_flatten, gru, image_flatten], axis=-1)

    classification_output = create_classification_layers(concatenated)

    model = models.Model(
        [structure_input, token_input, segment_input, image_input],
        classification_output,
    )

    rms = optimizers.RMSprop(learning_rate=learning_rate)

    model.compile(
        optimizer=rms,
        loss=DEFAULT_LOSS,
        metrics=DEFAULT_METRICS,
    )
    return model


class BertConfig:
    """
    Configuration class to store the configuration of a `BertModel`.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.name = kwargs.pop("name", "BertEmbedding")
        self.vocab_size = kwargs.pop("vocab_size", 30000)
        self.type_vocab_size = kwargs.pop("type_vocab_size", 300)
        self.hidden_size = kwargs.pop("hidden_size", 768)
        self.num_hidden_layers = kwargs.pop("num_hidden_layers", 12)
        self.num_attention_heads = kwargs.pop("num_attention_heads", 12)
        self.intermediate_size = kwargs.pop("intermediate_size", 3072)
        self.hidden_activation = kwargs.pop("hidden_activation", "gelu")
        self.hidden_dropout_rate = kwargs.pop("hidden_dropout_rate", 0.1)
        self.attention_dropout_rate = kwargs.pop("attention_dropout_rate", 0.1)
        self.max_position_embeddings = kwargs.pop("max_position_embeddings", 200)
        self.max_sequence_length = kwargs.pop("max_sequence_length", 200)


class BertEmbedding(keras.layers.Layer):
    """
    An own embedding layer that can be used for both token embeddings and
    segment embeddings in the BERT model.
    """

    config = None

    def __init__(self, config):
        super().__init__(name=config.name)
        self.config = config

        self.token_embedding = self.add_weight(
            shape=[self.config.vocab_size, self.config.hidden_size],
            initializer=keras.initializers.TruncatedNormal(stddev=0.02),
        )
        self.position_embedding = keras.layers.Embedding(
            config.max_position_embeddings,
            config.hidden_size,
            embeddings_initializer=keras.initializers.TruncatedNormal(stddev=0.02),
            name="position_embedding",
        )
        self.token_type_embedding = keras.layers.Embedding(
            config.type_vocab_size,
            config.hidden_size,
            embeddings_initializer=keras.initializers.TruncatedNormal(stddev=0.02),
            name="token_type_embedding",
        )
        self.layer_norm = keras.layers.LayerNormalization(
            epsilon=1e-12, name="LayerNorm"
        )
        self.dropout = keras.layers.Dropout(config.hidden_dropout_rate)

    def build(self, input_shape):
        """
        Build the layer.
        """
        super().build(input_shape)

    def call(self, inputs: tf.Tensor, training: bool = False, mode: str = "embedding"):
        """
        Forward pass of the layer.
        """
        # used for masked lm
        if mode == "linear":
            return tf.matmul(inputs, self.token_embedding, transpose_b=True)

        # used for sentence classification
        input_ids, token_type_ids = inputs
        input_ids = tf.cast(input_ids, dtype=tf.int32)
        position_ids = tf.range(input_ids.shape[1], dtype=tf.int32)[tf.newaxis, :]
        if token_type_ids is None:
            token_type_ids = tf.fill(input_ids.shape.as_list(), 0)

        # create embeddings
        position_embeddings = self.position_embedding(position_ids)
        token_type_embeddings = self.token_type_embedding(token_type_ids)
        token_embeddings = tf.gather(self.token_embedding, input_ids)

        # sum embeddings
        embeddings = token_embeddings + token_type_embeddings + position_embeddings
        embeddings = self.layer_norm(embeddings)
        return self.dropout(embeddings, training=training)

    def get_config(self):
        """
        Get the configuration of the layer.
        :return: The configuration.
        """
        config = super().get_config()
        config.update(self.config.__dict__)
        return config

    @classmethod
    def from_config(cls, config):
        """
        Create a layer from the configuration.
        :param config: The configuration.
        :return: The layer.
        """
        return cls(BertConfig(**config))
