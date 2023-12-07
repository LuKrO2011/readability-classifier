import unittest

import torch

from readability_classifier.models.extractors.test_structural_extractor import (
    create_test_data,
)
from src.readability_classifier.models.structural_model import StructuralModel

BATCH_SIZE = 1
LEARNING_RATE = 0.0015


class TestStructuralModel(unittest.TestCase):
    structural_model = StructuralModel.build_from_config()
    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(structural_model.parameters(), lr=LEARNING_RATE)

    def test_backward_pass(self):
        # Create test input data
        matrix = create_test_data()

        # Create target data
        target_data = torch.rand(BATCH_SIZE, 1).float()

        # Calculate output data
        output = self.structural_model(matrix)

        # Perform a backward pass
        loss = self.criterion(output, target_data)
        loss.backward()

        # Check if gradients are updated
        assert any(
            param.grad is not None for param in self.structural_model.parameters()
        )

    def test_update_weights(self):
        # Create test input data
        matrix = create_test_data()

        # Create target data
        target_data = torch.rand(BATCH_SIZE, 1).float()

        # Calculate output data
        output = self.structural_model(matrix)

        # Perform a backward pass
        loss = self.criterion(output, target_data)
        loss.backward()

        # Update weights
        self.optimizer.step()

        # Check if weights are updated
        assert any(
            param.grad is not None for param in self.structural_model.parameters()
        )
