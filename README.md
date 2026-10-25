# 🥗 FoodVerse AI — Multimodal Food Intelligence Platform

> **NASSCOM FutureSkills Prime · Vibe Coding Capstone Project**  
> Built with Google Gemini 1.5 Flash Vision + Streamlit

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## 🌟 What It Does

FoodVerse AI is a multimodal food intelligence platform powered by Google Gemini Vision that turns any food photo into actionable health insights in seconds.

### Three Core Features:

| Feature | What it analyzes |
|:---|:---|
| 🍽️ **Nutrition Analyzer** | Identifies the dish, estimates macros (calories, protein, carbs, fat, fiber), micronutrients, allergens, diet suitability, and AI health recommendations |
| 🔬 **Freshness Detector** | Scans produce and perishables for spoilage signs, estimates remaining shelf life in days, and recommends optimal storage |
| 🏥 **Kitchen Hygiene Audit** | Performs an FSSAI-style hygiene compliance inspection scoring cleanliness, organization, food storage, pest control, and temperature control |

---

## 🚀 Setup & Run Locally

### Prerequisites
- Python 3.9+
- A free [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Install & Launch

```bash
# Clone the repository
git clone https://github.com/sahajkaurg/food-verse-ai.git
cd food-verse-ai

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### Set Your API Key
Enter your Gemini API key in the sidebar when the app opens. Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

---

## 🏗️ Architecture

```
User Photo Upload
        ↓
Google Gemini 1.5 Flash Vision API
        ↓
Structured JSON Response Parsing
        ↓
┌─────────────────────────────────┐
│  Nutrition Engine               │  → Macros, micros, allergens, diet tags
│  Freshness Engine               │  → Spoilage score, shelf life, storage tips
│  Hygiene Audit Engine           │  → 5-category compliance scoring
└─────────────────────────────────┘
        ↓
Interactive Streamlit Dashboard
(Plotly charts, gauges, metric cards)
```

---

## 📁 Project Structure

```
food-verse-ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | Streamlit |
| **AI Vision** | Google Gemini 1.5 Flash |
| **Charts** | Plotly |
| **Data** | Pandas |
| **Image Processing** | Pillow |

---

## 📸 Example Use Cases

- 📱 **Snap & Track** — Take a photo of your meal and instantly know its calories and macros
- 🛒 **Smart Grocery** — Check if that avocado or mango is still fresh before buying
- 🍽️ **Restaurant Compliance** — Audit kitchen hygiene with a single photo for FSSAI readiness

---

## 📄 License

MIT License — free to use, modify, and distribute.
