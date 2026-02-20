import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import torch
import torch.optim as optim  # Use the standard PyTorch optimizer
import numpy as np
from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import DataLoader, Dataset

# 1. Load Knowledge and sync ALL_SKILLS
with open('skills_knowledge.json', 'r') as f:
    knowledge = json.load(f)

# This creates the "Master List" the AI will learn
ALL_SKILLS = []
for job in knowledge.values():
    for tier in job.values():
        for skill in tier:
            if skill not in ALL_SKILLS:
                ALL_SKILLS.append(skill)
ALL_SKILLS = sorted(ALL_SKILLS)

class CareerDataset(Dataset):
    def __init__(self, knowledge, tokenizer):
        self.samples = []
        for job_title, tiers in knowledge.items():
            target_vector = np.zeros(len(ALL_SKILLS))
            for tier_skills in tiers.values():
                for s in tier_skills:
                    target_vector[ALL_SKILLS.index(s)] = 1
            self.samples.append((job_title, target_vector))
        self.tokenizer = tokenizer

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        title, target = self.samples[idx]
        inputs = self.tokenizer(title, padding='max_length', max_length=32, truncation=True, return_tensors="pt")
        return inputs['input_ids'].squeeze(0), inputs['attention_mask'].squeeze(0), torch.tensor(target, dtype=torch.float)

# Setup
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=len(ALL_SKILLS))
dataset = CareerDataset(knowledge, tokenizer)
loader = DataLoader(dataset, batch_size=2, shuffle=True)

optimizer = AdamW(model.parameters(), lr=5e-5)
model.train()

print(f"Training on {len(ALL_SKILLS)} unique skills...")

# Training Loop
for epoch in range(60): # Increased epochs for better accuracy
    total_loss = 0
    for ids, mask, targets in loader:
        optimizer.zero_grad()
        outputs = model(ids, attention_mask=mask).logits
        loss = torch.nn.BCEWithLogitsLoss()(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    
    if epoch % 10 == 0:
        print(f"Epoch {epoch} | Loss: {total_loss/len(loader):.4f}")

# Save the Brain
output_dir = 'final_skill_model'
if not os.path.exists(output_dir): os.makedirs(output_dir)

model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

# Save the metadata so predictor.py knows which index belongs to which skill
with open(os.path.join(output_dir, 'skill_meta.json'), 'w') as f:
    json.dump({"all_skills": ALL_SKILLS}, f)

print("✅ Model trained and saved successfully!")