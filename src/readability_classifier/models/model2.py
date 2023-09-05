from sklearn.metrics import mean_squared_error
from transformers import BertTokenizer, BertModel
import torch
import os
import pandas as pd
from sklearn.model_selection import train_test_split
import torch.nn as nn
import torch.optim as optim


class CNNModel(nn.Module):
    def __init__(self, num_classes):
        super(CNNModel, self).__init__()

        # Bert embedding
        self.bert = BertModel.from_pretrained('bert-base-uncased')

        # Convolutional layers
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=(3, 768))
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 1))

        # Max-pooling layers
        self.pool = nn.MaxPool2d(kernel_size=(2, 1))

        # Fully connected layers
        self.fc1 = nn.Linear(64 * 49, 128)  # TODO: Adjust
        self.fc2 = nn.Linear(128, num_classes)

        # Dropout layer to reduce overfitting
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        # Bert embedding
        x = self.bert(x)[0]

        # Apply convolutional and pooling layers
        x = self.pool(nn.functional.relu(self.conv1(x)))
        x = self.pool(nn.functional.relu(self.conv2(x)))

        # Flatten the feature map
        x = x.view(-1, 64 * 49)  # TODO: Adjust

        # Apply fully connected layers with dropout
        x = self.dropout(nn.functional.relu(self.fc1(x)))
        x = self.fc2(x)

        return x


class CodeReadabilityClassifier:
    def __init__(self, batch_size=32, num_epochs=10,
                 learning_rate=0.001):
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.learning_rate = learning_rate
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def prepare_data(self, csv, data_dir):
        """
        Loads the data and prepares it for training and evaluation.
        :param csv: Path to the CSV file containing the scores.
        :param data_dir: Path to the directory containing the code snippets.
        :return: None
        """
        code_snippets, aggregated_scores = self.load_data(csv, data_dir)
        embeddings = [self.tokenize_and_encode(code) for code in code_snippets]

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            embeddings,
            aggregated_scores,
            test_size=0.2,
            random_state=42)

        self.setup_model()

    def load_data(self, csv, data_dir):
        df = pd.read_csv(csv)
        num_columns = df.shape[1]

        # TODO: Actually load the code snippets

        code_snippets = []
        for i in range(1, num_columns):
            column_name = f'Snippet{i}'
            code_snippets.append(df[column_name].tolist())

        evaluator_scores = df.drop(columns=['', *code_snippets])
        aggregated_scores = evaluator_scores.mean(axis=1)

        return code_snippets, aggregated_scores

    def tokenize_and_encode(self, text):
        tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        input_ids = tokenizer.encode(text, add_special_tokens=True)
        input_ids = torch.tensor(input_ids).unsqueeze(0)  # TODO: Add batch dimension?
        with torch.no_grad():
            embeddings = self.model.bert(input_ids)[0]
        return embeddings

    def setup_model(self):
        self.model = CNNModel(2)
        self.model.to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

    def _train_iteration(self, x_batch, y_batch):
        self.optimizer.zero_grad()
        outputs = self.model(x_batch)
        loss = self.criterion(outputs, y_batch)
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def train(self):
        for epoch in range(self.num_epochs):
            self.model.train()
            running_loss = 0.0

            for i in range(0, len(self.X_train), self.batch_size):
                # x, y = x.to(device), y.to(device)
                x_batch = torch.Tensor(self.X_train[i:i + self.batch_size]).to(
                    self.device)
                y_batch = torch.Tensor(self.y_train[i:i + self.batch_size]).unsqueeze(
                    1).to(self.device)

                loss = self._train_iteration(x_batch, y_batch)
                running_loss += loss

            print(
                f"Epoch {epoch + 1}/{self.num_epochs}, Loss: {running_loss / len(self.X_train)}")

    def evaluate(self):
        self.model.eval()
        with torch.no_grad():
            # x, y = x.to(device), y.to(device)
            x_batch = torch.Tensor(self.X_test).to(self.device)
            y_batch = torch.Tensor(self.y_test).unsqueeze(1).to(self.device)
            predictions = self.model(x_batch)

        mse = mean_squared_error(y_batch.cpu().numpy(), predictions.cpu().numpy())
        print(f"Mean Squared Error (MSE): {mse}")


if __name__ == "__main__":
    data_dir = 'C:/Users/lukas/Meine Ablage/Uni/{SoSe23/Masterarbeit/Datasets/Dataset/Dataset/'
    snippets_dir = os.path.join(data_dir, 'Snippets')
    csv = os.path.join(data_dir, 'scores.csv')

    classifier = CodeReadabilityClassifier()
    classifier.prepare_data(csv, snippets_dir)
    classifier.train()
    classifier.evaluate()
