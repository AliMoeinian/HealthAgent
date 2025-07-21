# 🏋️ AI Health & Fitness Agents System

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-0.1.0-orange)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Gemma3-purple)

A personalized health coaching system with three specialized AI agents that generate fitness plans, nutrition guides, and wellness recommendations.
This Repository is going to Get Advanced soon!

## ✨ Features

- **Fitness Trainer Agent**  
  🏋️ Creates customized workout plans based on:  
  - Fitness level (Beginner/Intermediate/Advanced)  
  - Available equipment (Home/Gym)  
  - Injury restrictions  

- **Nutritionist Agent**  
  🥗 Designs meal plans with:  
  - Dietary preferences (Vegan/Keto/Mediterranean)  
  - Allergies/Sensitivities  
  - Caloric targets  

- **Health Advisor Agent**  
  💆 Provides holistic recommendations for:  
  - Sleep optimization  
  - Stress management  
  - Habit formation  

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- OpenRouter API key ([Get yours here](https://openrouter.ai/))

### Installation
```bash
# Clone the repository
git clone https://github.com/AliMoeinian/HealthAgent.git

# Install dependencies
pip install -r requirements.txt

# Set up environment
Add your OpenRouter Key (or any API Key) to: apikey.env
`NOTE`: If you don't use the OpenRouter API,you have to make some changes to the file Agents.py, where I defined the model and API Path
```
---
Project Structure :
```bash
HealthAgent/
├── UserData/              # User profile storage
├── Results/               # Generated health plans
├── Utils/
│   └── Agents.py          # AI agent implementations
├── main.py                # Entry point
├── requirements.txt       # Dependencies
└── apikey.env             # API keys (ignored by Git)
```
---
