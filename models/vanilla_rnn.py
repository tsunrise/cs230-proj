import torch
import torch.nn as nn
import numpy as np
from models.model_utils import ConcatPrev


class DeepBeatsVanillaRNN(nn.Module):
    def __init__(self, num_notes, embed_size, hidden_dim):
        super(DeepBeatsVanillaRNN, self).__init__()
        self.num_notes = num_notes
        self.note_embedding = nn.Embedding(num_notes, embed_size)
        self.concat_prev = ConcatPrev()
        self.concat_input_fc = nn.Linear(embed_size + 2, embed_size + 2)
        self.concat_input_activation = nn.LeakyReLU()
        self.layer1 = nn.RNN(embed_size + 2, hidden_dim, batch_first=True)
        self.layer2 = nn.RNN(hidden_dim, hidden_dim, batch_first=True)
        self.notes_output = nn.Linear(hidden_dim, num_notes)

        self._initializer_weights()

    def _default_init_hidden(self, batch_size):
        device = next(self.parameters()).device
        h1_0 = torch.zeros(1, batch_size, self.layer1.hidden_size).to(device)
        h2_0 = torch.zeros(1, batch_size, self.layer2.hidden_size).to(device)
        return h1_0, h2_0

    def _initializer_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.constant_(m.bias, 0)

    def forward(self, x, y_prev, init_hidden = None):
        h1_0, h2_0 = self._default_init_hidden(x.shape[0]) if init_hidden is None else init_hidden
        y_prev_embed = self.note_embedding(y_prev)
        X = self.concat_prev(x, y_prev_embed)
        # Concat input
        X_fc = self.concat_input_fc(X)
        X_fc = self.concat_input_activation(X_fc)
        # residual connection
        X = X_fc + X
        X, h1 = self.layer1(X, h1_0)
        X, h2 = self.layer2(X, h2_0)
        predicted_notes = self.notes_output(X)
        return predicted_notes, (h1, h2)

    def loss_function(self, pred, target):
        criterion = nn.CrossEntropyLoss()
        target = target.flatten() # (batch_size * seq_len)
        pred = pred.reshape(-1, pred.shape[-1]) # (batch_size * seq_len, num_notes)
        loss = criterion(pred, target)
        return loss

    def clip_gradients_(self, max_value):
        torch.nn.utils.clip_grad.clip_grad_value_(self.parameters(), max_value)
