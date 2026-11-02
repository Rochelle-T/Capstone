"""
model_def.py
============
WindowCNN + AttentionMIL, copied UNCHANGED from the training notebook
(exoplanet_cnn_window_B_colab). Do not edit layer shapes/order: the saved
state_dict (final_model.pt) must match exactly.

Checkpoint hyper-parameters (from training, Experiment B):
    dropout = 0.25, window_chunk_size = 256
Input to AttentionMIL.forward: a LIST of bags, each a float32 tensor [W, 1024]
(W = number of windows for one KIC, <= 32), values = flux_processed - 1.0.
Output: (logits [B], list of attention-weight tensors [W]).
"""

import torch
import torch.nn as nn

# AttentionMIL.encode_bag moves each chunk to this global device (as in training).
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class WindowCNN(nn.Module):

    def __init__(self, dropout=0.25):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=11, padding=5),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),

            nn.Conv1d(32, 64, kernel_size=9, padding=4),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),

            nn.Conv1d(64, 128, kernel_size=7, padding=3),
            nn.BatchNorm1d(128),
            nn.ReLU(),

            nn.Conv1d(128, 128, kernel_size=5, padding=2),
            nn.BatchNorm1d(128),
            nn.ReLU(),

            nn.AdaptiveAvgPool1d(1)
        )

        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        z = self.features(x).squeeze(-1)
        return self.dropout(z)


class AttentionMIL(nn.Module):

    def __init__(self, dropout=0.25, window_chunk_size=256):
        super().__init__()

        self.encoder = WindowCNN(dropout)

        self.attention = nn.Sequential(
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )

        self.classifier = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

        self.window_chunk_size = window_chunk_size

    def encode_bag(self, x):
        # x: [W, 1024]
        embeddings = []

        for start in range(0, x.shape[0], self.window_chunk_size):
            chunk = x[start:start + self.window_chunk_size]
            chunk = chunk.to(DEVICE, non_blocking=True)
            chunk = chunk.unsqueeze(1)
            z = self.encoder(chunk)
            embeddings.append(z)

        return torch.cat(embeddings, dim=0)

    def forward(self, bags):
        logits_out = []
        weights_out = []

        for x in bags:
            z = self.encode_bag(x)
            scores = self.attention(z).squeeze(-1)
            weights = torch.softmax(scores, dim=0)
            bag = torch.sum(z * weights.unsqueeze(-1), dim=0)
            logits = self.classifier(bag).squeeze(-1)

            logits_out.append(logits)
            weights_out.append(weights)

        return torch.stack(logits_out), weights_out


# ----------------------------------------------------------------------------
# Usage with kepler_pipeline.py
# ----------------------------------------------------------------------------
# from model_def import AttentionMIL, DEVICE
# from kepler_pipeline import prepare_kic, load_final_model, predict_bag
#
# model, threshold, cfg = load_final_model("final_model.pt", AttentionMIL, device=DEVICE)
# bag = prepare_kic("KIC 9850966")
# print(predict_bag(model, bag, threshold))
