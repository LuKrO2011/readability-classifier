import pytest
import torch

from src.readability_classifier.models.model import CNNModel

EMBEDDED_MIN = 1
EMBEDDED_MAX = 9999
TOKEN_LENGTH = 512
BATCH_SIZE = 1
SHAPE = (BATCH_SIZE, TOKEN_LENGTH)
NUM_CLASSES = 1
NUM_EPOCHS = 1
LEARNING_RATE = 0.001


@pytest.fixture()
def model():
    return CNNModel(num_classes=NUM_CLASSES)


@pytest.fixture()
def criterion():
    return torch.nn.MSELoss()


@pytest.fixture()
def optimizer(model):
    return torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)


def test_forward_pass(model):
    # Create test x_batch with shape (1, 512) and values between 1 and 9999
    input_data = torch.randint(EMBEDDED_MIN, EMBEDDED_MAX, SHAPE).long()

    # Create test attention mask with shape (1, 512)
    attention_mask = torch.ones(SHAPE).long()

    # Perform a forward pass
    output = model(input_data, attention_mask)

    # Check if the output has the expected shape
    assert output.shape == (NUM_CLASSES, BATCH_SIZE)


def test_backward_pass(model, criterion):
    # Create test x_batch with shape (1, 512) and values between 1 and 9999
    input_data = torch.randint(EMBEDDED_MIN, EMBEDDED_MAX, SHAPE).long()

    # Create test attention mask with shape (1, 512)
    attention_mask = torch.ones(SHAPE).long()

    # Create target data
    target_data = torch.rand(8, 1).float()

    # Calculate output data
    output_data = model(input_data, attention_mask)

    # Perform a backward pass
    loss = criterion(output_data, target_data)
    loss.backward()

    # Check if gradients are updated
    assert any(param.grad is not None for param in model.parameters())


def test_prediction(model):
    pass
