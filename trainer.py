import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import torch
import torch.optim as optim
from torch.optim import AdamW
import numpy as np
from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import DataLoader, Dataset

# 1. Load Knowledge and sync ALL_SKILLS
with open('skills_knowledge.json', 'r') as f:
    knowledge = json.load(f)

# This creates the "Master List" the AI will learn
ALL_SKILLS = []
for job in knowledge.values():
    for tier in ["beginner", "compulsory", "intermediate", "advanced"]:
        tier_skills = job.get(tier, [])
        for skill in tier_skills:
            if skill not in ALL_SKILLS:
                ALL_SKILLS.append(skill)
ALL_SKILLS = sorted(ALL_SKILLS)

class CareerDataset(Dataset):
    def __init__(self, knowledge, tokenizer):
        self.samples = []
        for job_title, tiers in knowledge.items():
            target_vector = np.zeros(len(ALL_SKILLS))
            for tier in ["beginner", "compulsory", "intermediate", "advanced"]:
                tier_skills = tiers.get(tier, [])
                for s in tier_skills:
                    if s in ALL_SKILLS:
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
loader = DataLoader(dataset, batch_size=4, shuffle=True)

optimizer = AdamW(model.parameters(), lr=5e-5)
model.train()

print(f"Training on {len(ALL_SKILLS)} unique skills across {len(knowledge)} job titles...")

# Training Loop
for epoch in range(20): # 20 epochs is enough for this tiny set
    total_loss = 0
    for ids, mask, targets in loader:
        optimizer.zero_grad()
        outputs = model(ids, attention_mask=mask).logits
        loss = torch.nn.BCEWithLogitsLoss()(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    
    if epoch % 5 == 0:
        print(f"Epoch {epoch} | Loss: {total_loss/len(loader):.4f}")

# Save the Brain
output_dir = 'final_skill_model'
if not os.path.exists(output_dir): os.makedirs(output_dir)

model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

# Save the metadata including the full tiered structure for each domain
# This removes dependency on skills_knowledge.json during prediction
with open(os.path.join(output_dir, 'skill_meta.json'), 'w') as f:
    json.dump({
        "all_skills": ALL_SKILLS,
        "structured_data": knowledge
    }, f, indent=4)

print("✅ Model trained and saved successfully with full structural metadata!")
