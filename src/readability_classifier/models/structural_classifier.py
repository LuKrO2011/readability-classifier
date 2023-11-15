from pathlib import Path

import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from readability_classifier.models.base_classifier import BaseClassifier
from readability_classifier.models.structural_model import StructuralModel
from readability_classifier.utils.config import (
    DEFAULT_MODEL_BATCH_SIZE,
    ModelInput,
    StructuralInput,
)


class StructuralClassifier(BaseClassifier):
    """
    A code readability classifier based on a CNN model. The model can be used to predict
    the readability of a code snippet.
    The model is trained on code snippets and their corresponding scores. The model uses
    the structural features (ASCII matrix) of the code snippets.
    """

    def __init__(
        self,
        train_loader: DataLoader = None,
        test_loader: DataLoader = None,
        validation_loader: DataLoader = None,
        store_dir: Path = None,
        batch_size: int = DEFAULT_MODEL_BATCH_SIZE,
        num_epochs: int = 20,
        learning_rate: float = 0.0015,
    ):
        """
        Initializes the classifier.
        :param train_loader: The data loader for the training data.
        :param test_loader: The data loader for the test data.
        :param validation_loader: The data loader for the validation data.
        :param batch_size: The batch size.
        :param num_epochs: The number of epochs.
        :param learning_rate: The learning rate.
        """
        model = StructuralModel.build_from_config()
        criterion = nn.MSELoss()
        optimizer = optim.RMSprop(model.parameters(), lr=learning_rate)

        super().__init__(
            model=model,
            criterion=criterion,
            optimizer=optimizer,
            train_loader=train_loader,
            test_loader=test_loader,
            validation_loader=validation_loader,
            store_dir=store_dir,
            batch_size=batch_size,
            num_epochs=num_epochs,
            learning_rate=learning_rate,
        )

    def _batch_to_input(self, batch: dict) -> ModelInput:
        """
        Converts a batch to a model input and sends it to the device.
        :param batch: The batch to convert.
        :return: The model input.
        """
        matrix, _, _, _, _ = self._extract(batch)
        matrix = self._to_device(matrix)
        return StructuralInput(matrix)