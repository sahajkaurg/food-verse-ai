import streamlit as st
import google.generativeai as genai
import json
import re
import io
import os
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FoodVerse AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main { background: linear-gradient(135deg, #0f1b12 0%, #1a2e1e 100%); }
    
    .hero-card {
        background: linear-gradient(135deg, #1e4620 0%, #2d6a31 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid #3d8b42;
        box-shadow: 0 8px 32px rgba(61, 139, 66, 0.3);
    }
    
    .metric-card {
        background: rgba(30, 70, 32, 0.4);
        border: 1px solid #3d8b42;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #7dff8a;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #9cb8a0;
        margin-top: 0.4rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-unit {
        font-size: 0.9rem;
        color: #5a9b60;
        font-weight: 400;
    }
    
    .result-section {
        background: rgba(20, 45, 22, 0.6);
        border: 1px solid #2d6a31;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .badge {
        display: inline-block;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .badge-green { background: #1e4620; color: #7dff8a; border: 1px solid #3d8b42; }
    .badge-yellow { background: #3d3008; color: #ffd700; border: 1px solid #8b7000; }
    .badge-red { background: #3d0808; color: #ff7d7d; border: 1px solid #8b0000; }
    
    .stButton > button {
        background: linear-gradient(135deg, #2d6a31, #3d8b42);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.7rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #3d8b42, #4da854);
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(61,139,66,0.4);
    }

    div[data-testid="stFileUploader"] {
        border: 2px dashed #3d8b42;
        border-radius: 16px;
        padding: 1rem;
    }
    
    .sidebar-section {
        background: rgba(20, 45, 22, 0.5);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #2d6a31;
    }
    
    h1, h2, h3 { color: #7dff8a !important; }
    p, li { color: #c8e6ca; }
    
    .warning-box {
        background: rgba(61, 48, 8, 0.6);
        border: 1px solid #8b7000;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .danger-box {
        background: rgba(61, 8, 8, 0.6);
        border: 1px solid #8b0000;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .success-box {
        background: rgba(8, 61, 12, 0.6);
        border: 1px solid #007b00;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Gemini Setup ──────────────────────────────────────────────────────────────
def get_gemini_model():
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def extract_json(text: str) -> dict:
    """Robustly extract the first JSON object from a model response."""
    text = text.strip()
    # Try finding ```json ... ``` block
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Find first { ... } block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ── Analysis Functions ────────────────────────────────────────────────────────

def analyze_nutrition(model, image: Image.Image) -> dict:
    prompt = """You are an expert nutritionist and AI food analyst. Analyze this food image and provide a detailed JSON response.

Return ONLY a valid JSON object with this exact structure:
{
  "dish_name": "Name of the dish",
  "cuisine": "Type of cuisine",
  "confidence": 95,
  "serving_size": "1 plate (~350g)",
  "macros": {
    "calories": 450,
    "protein_g": 28,
    "carbohydrates_g": 45,
    "fat_g": 16,
    "fiber_g": 6,
    "sugar_g": 8,
    "sodium_mg": 680
  },
  "micronutrients": {
    "vitamin_c_mg": 15,
    "vitamin_a_iu": 800,
    "iron_mg": 3.5,
    "calcium_mg": 120,
    "potassium_mg": 450
  },
  "health_score": 72,
  "health_tags": ["High Protein", "Moderate Carbs", "Good Fiber"],
  "ingredients_detected": ["chicken", "rice", "vegetables", "olive oil"],
  "allergens": ["gluten"],
  "diet_suitability": {
    "vegetarian": false,
    "vegan": false,
    "gluten_free": false,
    "keto": false,
    "diabetic_friendly": true
  },
  "recommendations": [
    "Great protein source for muscle building",
    "Consider adding more colorful vegetables for antioxidants",
    "Moderate portion for weight management"
  ]
}"""
    try:
        response = model.generate_content([prompt, image])
        data = extract_json(response.text)
        return data if data else {}
    except Exception as e:
        st.error(f"Nutrition analysis failed: {e}")
        return {}


def analyze_freshness(model, image: Image.Image) -> dict:
    prompt = """You are an expert food safety inspector and AI freshness analyst. Analyze this food/produce image for freshness and spoilage.

Return ONLY a valid JSON object with this exact structure:
{
  "item_detected": "Name of the food item",
  "freshness_score": 85,
  "freshness_status": "Fresh",
  "days_remaining": 4,
  "confidence": 90,
  "visual_indicators": {
    "color": "Normal vibrant color",
    "texture": "Firm and smooth",
    "surface": "No visible blemishes",
    "mold_detected": false,
    "discoloration": false,
    "wilting": false
  },
  "spoilage_signs": [],
  "safe_to_consume": true,
  "storage_recommendation": "Store in refrigerator at 2-4°C in a sealed container",
  "shelf_life_tips": [
    "Keep away from ethylene-producing fruits",
    "Maintain humidity around 90%"
  ],
  "risk_level": "Low",
  "action_required": "No action needed - item is fresh"
}

Freshness status must be one of: "Fresh", "Good", "Fair", "Poor", "Spoiled"
Risk level must be one of: "Low", "Medium", "High", "Critical" """
    try:
        response = model.generate_content([prompt, image])
        data = extract_json(response.text)
        return data if data else {}
    except Exception as e:
        st.error(f"Freshness analysis failed: {e}")
        return {}


def analyze_hygiene(model, image: Image.Image) -> dict:
    prompt = """You are a certified food safety auditor and kitchen hygiene inspector. Analyze this kitchen/food preparation area image.

Return ONLY a valid JSON object with this exact structure:
{
  "area_type": "Kitchen counter / Prep area / Storage",
  "overall_hygiene_score": 78,
  "compliance_status": "Compliant",
  "inspection_date": "2026-10-25",
  "categories": {
    "cleanliness": {
      "score": 80,
      "status": "Good",
      "observations": ["Surfaces appear clean", "No visible grease buildup"]
    },
    "organization": {
      "score": 75,
      "status": "Good",
      "observations": ["Items properly stored", "Good separation of raw and cooked"]
    },
    "food_storage": {
      "score": 85,
      "status": "Excellent",
      "observations": ["Proper container usage", "Labels visible"]
    },
    "pest_control": {
      "score": 95,
      "status": "Excellent",
      "observations": ["No visible pest signs", "Area sealed properly"]
    },
    "temperature_control": {
      "score": 70,
      "status": "Fair",
      "observations": ["Temperature indicators not visible in frame"]
    }
  },
  "violations": [],
  "recommendations": [
    "Ensure all containers are labeled with dates",
    "Maintain clear separation between prep zones"
  ],
  "critical_issues": [],
  "certification_eligible": true
}

Compliance status must be one of: "Excellent", "Compliant", "Needs Improvement", "Non-Compliant" """
    try:
        response = model.generate_content([prompt, image])
        data = extract_json(response.text)
        return data if data else {}
    except Exception as e:
        st.error(f"Hygiene analysis failed: {e}")
        return {}


# ── Rendering Functions ───────────────────────────────────────────────────────

def render_macro_chart(macros: dict):
    labels = ["Protein", "Carbohydrates", "Fat", "Fiber"]
    values = [
        macros.get("protein_g", 0),
        macros.get("carbohydrates_g", 0),
        macros.get("fat_g", 0),
        macros.get("fiber_g", 0),
    ]
    colors = ["#4ade80", "#60a5fa", "#f97316", "#a78bfa"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0f1b12", width=2)),
        textinfo="label+percent",
        textfont=dict(size=13, color="white"),
        hovertemplate="%{label}: %{value}g<extra></extra>",
    )])

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=20, r=20),
        height=260,
        annotations=[dict(
            text=f"<b>{macros.get('calories', 0)}</b><br>kcal",
            x=0.5, y=0.5,
            font=dict(size=16, color="#7dff8a"),
            showarrow=False,
        )],
    )
    return fig


def render_health_gauge(score: int, title: str = "Health Score"):
    color = "#4ade80" if score >= 70 else "#facc15" if score >= 45 else "#f87171"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title=dict(text=title, font=dict(color="#c8e6ca", size=14)),
        number=dict(font=dict(color=color, size=36)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor="#3d8b42", tickfont=dict(color="#9cb8a0")),
            bar=dict(color=color, thickness=0.7),
            bgcolor="rgba(20,45,22,0.5)",
            bordercolor="#2d6a31",
            steps=[
                dict(range=[0, 45], color="rgba(61,8,8,0.3)"),
                dict(range=[45, 70], color="rgba(61,48,8,0.3)"),
                dict(range=[70, 100], color="rgba(8,61,12,0.3)"),
            ],
            threshold=dict(line=dict(color=color, width=3), thickness=0.8, value=score),
        )
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=20, l=30, r=30),
        height=220,
        font=dict(color="#c8e6ca"),
    )
    return fig


def freshness_color(score: int):
    if score >= 75: return "#4ade80"
    if score >= 50: return "#facc15"
    if score >= 25: return "#f97316"
    return "#f87171"


def render_nutrition_results(data: dict):
    if not data:
        st.warning("Could not extract nutrition data. Please try with a clearer food image.")
        return

    st.markdown(f"""
    <div class="hero-card">
        <h2 style="margin:0;font-size:1.8rem;">🍽️ {data.get('dish_name', 'Unknown Dish')}</h2>
        <p style="color:#9cb8a0;margin:0.3rem 0 0 0;">{data.get('cuisine', '')} · Serving: {data.get('serving_size', 'N/A')} · Confidence: {data.get('confidence', 0)}%</p>
    </div>
    """, unsafe_allow_html=True)

    macros = data.get("macros", {})
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        (col1, str(macros.get("calories", "—")), "kcal", "Calories"),
        (col2, str(macros.get("protein_g", "—")), "g", "Protein"),
        (col3, str(macros.get("carbohydrates_g", "—")), "g", "Carbohydrates"),
        (col4, str(macros.get("fat_g", "—")), "g", "Fat"),
    ]
    for col, val, unit, label in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}<span class="metric-unit"> {unit}</span></div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_chart, col_gauge = st.columns([1, 1])

    with col_chart:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 🥧 Macro Distribution")
        st.plotly_chart(render_macro_chart(macros), use_container_width=True, key="macro_pie")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_gauge:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 💚 Health Score")
        st.plotly_chart(render_health_gauge(data.get("health_score", 0)), use_container_width=True, key="health_gauge")
        tags = data.get("health_tags", [])
        if tags:
            badges_html = " ".join([f'<span class="badge badge-green">{t}</span>' for t in tags])
            st.markdown(badges_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("📊 Full Nutritional Breakdown"):
        micro = data.get("micronutrients", {})
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Macros**")
            macro_df = pd.DataFrame([
                {"Nutrient": "Calories", "Amount": macros.get("calories", 0), "Unit": "kcal"},
                {"Nutrient": "Protein", "Amount": macros.get("protein_g", 0), "Unit": "g"},
                {"Nutrient": "Carbohydrates", "Amount": macros.get("carbohydrates_g", 0), "Unit": "g"},
                {"Nutrient": "Fat", "Amount": macros.get("fat_g", 0), "Unit": "g"},
                {"Nutrient": "Fiber", "Amount": macros.get("fiber_g", 0), "Unit": "g"},
                {"Nutrient": "Sugar", "Amount": macros.get("sugar_g", 0), "Unit": "g"},
                {"Nutrient": "Sodium", "Amount": macros.get("sodium_mg", 0), "Unit": "mg"},
            ])
            st.dataframe(macro_df, hide_index=True, use_container_width=True)
        with cols[1]:
            st.markdown("**Micronutrients**")
            micro_df = pd.DataFrame([
                {"Nutrient": k.replace("_", " ").title(), "Amount": v, "Unit": "varies"}
                for k, v in micro.items()
            ])
            if not micro_df.empty:
                st.dataframe(micro_df, hide_index=True, use_container_width=True)

    with st.expander("🥗 Diet & Allergen Info"):
        diets = data.get("diet_suitability", {})
        allergens = data.get("allergens", [])
        col_d, col_a = st.columns(2)
        with col_d:
            st.markdown("**Diet Suitability**")
            for k, v in diets.items():
                icon = "✅" if v else "❌"
                st.markdown(f"{icon} {k.replace('_', ' ').title()}")
        with col_a:
            st.markdown("**Allergens Detected**")
            if allergens:
                for a in allergens:
                    st.markdown(f'<span class="badge badge-yellow">⚠️ {a}</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge badge-green">✅ No common allergens</span>', unsafe_allow_html=True)

    recs = data.get("recommendations", [])
    if recs:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 💡 AI Recommendations")
        for r in recs:
            st.markdown(f"• {r}")
        st.markdown('</div>', unsafe_allow_html=True)


def render_freshness_results(data: dict):
    if not data:
        st.warning("Could not extract freshness data. Try a clearer image of the food item.")
        return

    score = data.get("freshness_score", 0)
    status = data.get("freshness_status", "Unknown")
    risk = data.get("risk_level", "Unknown")
    safe = data.get("safe_to_consume", True)

    status_color = {
        "Fresh": "badge-green", "Good": "badge-green",
        "Fair": "badge-yellow", "Poor": "badge-red", "Spoiled": "badge-red"
    }.get(status, "badge-yellow")

    risk_color = {
        "Low": "badge-green", "Medium": "badge-yellow",
        "High": "badge-red", "Critical": "badge-red"
    }.get(risk, "badge-yellow")

    st.markdown(f"""
    <div class="hero-card">
        <h2 style="margin:0;font-size:1.8rem;">🔬 {data.get('item_detected', 'Food Item')}</h2>
        <p style="color:#9cb8a0;margin:0.5rem 0;">
            <span class="badge {status_color}">{status}</span>
            <span class="badge {risk_color}">Risk: {risk}</span>
            {'<span class="badge badge-green">✅ Safe to Eat</span>' if safe else '<span class="badge badge-red">⛔ Not Safe</span>'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{freshness_color(score)};">{score}</div>
            <div class="metric-label">Freshness Score /100</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        days = data.get("days_remaining", "—")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#60a5fa;">{days}</div>
            <div class="metric-label">Est. Days Remaining</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        conf = data.get("confidence", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#a78bfa;">{conf}%</div>
            <div class="metric-label">Detection Confidence</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_g, col_i = st.columns([1, 1])

    with col_g:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 📊 Freshness Gauge")
        st.plotly_chart(render_health_gauge(score, "Freshness Score"), use_container_width=True, key="fresh_gauge")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_i:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 🔍 Visual Indicators")
        indicators = data.get("visual_indicators", {})
        for k, v in indicators.items():
            if isinstance(v, bool):
                icon = "⚠️" if v and k in ["mold_detected", "discoloration", "wilting"] else ("✅" if not v else "ℹ️")
                st.markdown(f"{icon} **{k.replace('_', ' ').title()}**: {'Yes' if v else 'No'}")
            else:
                st.markdown(f"ℹ️ **{k.replace('_', ' ').title()}**: {v}")
        st.markdown('</div>', unsafe_allow_html=True)

    action = data.get("action_required", "")
    spoilage = data.get("spoilage_signs", [])
    if spoilage or not safe:
        st.markdown(f'<div class="danger-box">⛔ <b>Action Required:</b> {action}</div>', unsafe_allow_html=True)
        if spoilage:
            for s in spoilage:
                st.markdown(f"• {s}")
    else:
        st.markdown(f'<div class="success-box">✅ <b>Status:</b> {action}</div>', unsafe_allow_html=True)

    storage = data.get("storage_recommendation", "")
    tips = data.get("shelf_life_tips", [])
    if storage or tips:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 🧊 Storage Recommendations")
        if storage:
            st.markdown(f"**Optimal Storage:** {storage}")
        for tip in tips:
            st.markdown(f"• {tip}")
        st.markdown('</div>', unsafe_allow_html=True)


def render_hygiene_results(data: dict):
    if not data:
        st.warning("Could not extract hygiene data. Try a clearer image of the kitchen area.")
        return

    score = data.get("overall_hygiene_score", 0)
    status = data.get("compliance_status", "Unknown")
    eligible = data.get("certification_eligible", False)

    status_color = {
        "Excellent": "badge-green", "Compliant": "badge-green",
        "Needs Improvement": "badge-yellow", "Non-Compliant": "badge-red"
    }.get(status, "badge-yellow")

    st.markdown(f"""
    <div class="hero-card">
        <h2 style="margin:0;font-size:1.8rem;">🏥 Kitchen Hygiene Audit</h2>
        <p style="color:#9cb8a0;margin:0.5rem 0;">
            {data.get('area_type', 'Kitchen Area')} · Inspected: {data.get('inspection_date', datetime.now().strftime('%Y-%m-%d'))}
            <br>
            <span class="badge {status_color}">{status}</span>
            {'<span class="badge badge-green">🏆 Certification Eligible</span>' if eligible else '<span class="badge badge-red">❌ Not Yet Eligible</span>'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(render_health_gauge(score, "Hygiene Score"), use_container_width=True, key="hygiene_gauge")

    with col2:
        cats = data.get("categories", {})
        if cats:
            cat_names = list(cats.keys())
            cat_scores = [cats[c].get("score", 0) for c in cat_names]
            fig = go.Figure(go.Bar(
                y=[n.replace("_", " ").title() for n in cat_names],
                x=cat_scores,
                orientation="h",
                marker=dict(
                    color=["#4ade80" if s >= 70 else "#facc15" if s >= 45 else "#f87171" for s in cat_scores],
                    line=dict(color="rgba(0,0,0,0)", width=0),
                ),
                text=[f"{s}" for s in cat_scores],
                textposition="auto",
            ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(range=[0, 100], color="#9cb8a0", gridcolor="#1a3a1e"),
                yaxis=dict(color="#c8e6ca"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=220,
            )
            st.plotly_chart(fig, use_container_width=True, key="cat_bar")

    st.markdown("#### 🔍 Category Details")
    cats = data.get("categories", {})
    cols_per_row = 3
    cat_list = list(cats.items())
    for i in range(0, len(cat_list), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (cat_name, cat_data) in enumerate(cat_list[i:i+cols_per_row]):
            with cols[j]:
                cat_score = cat_data.get("score", 0)
                cat_status = cat_data.get("status", "")
                obs = cat_data.get("observations", [])
                box_class = "success-box" if cat_score >= 70 else "warning-box" if cat_score >= 45 else "danger-box"
                st.markdown(f"""
                <div class="{box_class}">
                    <b>{cat_name.replace('_', ' ').title()}</b><br>
                    <span style="font-size:1.5rem;font-weight:700;">{cat_score}</span>/100 · {cat_status}
                </div>
                """, unsafe_allow_html=True)
                for ob in obs:
                    st.markdown(f"<small>• {ob}</small>", unsafe_allow_html=True)

    critical = data.get("critical_issues", [])
    violations = data.get("violations", [])
    recs = data.get("recommendations", [])

    if critical:
        st.markdown('<div class="danger-box">', unsafe_allow_html=True)
        st.markdown("#### ⛔ Critical Issues")
        for c in critical:
            st.markdown(f"• {c}")
        st.markdown('</div>', unsafe_allow_html=True)

    if violations:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("#### ⚠️ Violations")
        for v in violations:
            st.markdown(f"• {v}")
        st.markdown('</div>', unsafe_allow_html=True)

    if recs:
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown("#### 💡 Recommendations")
        for r in recs:
            st.markdown(f"• {r}")
        st.markdown('</div>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0;">
        <h1 style="font-size:2.2rem;margin:0;">🥗</h1>
        <h2 style="margin:0.3rem 0;font-size:1.4rem;">FoodVerse AI</h2>
        <p style="color:#9cb8a0;font-size:0.85rem;margin:0;">Multimodal Food Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🔑 Gemini API Key**")
    api_key_input = st.text_input(
        "Enter your Gemini API key",
        type="password",
        placeholder="AIza...",
        help="Get your free key at aistudio.google.com",
        label_visibility="collapsed"
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input
        st.success("✅ API Key set")
    st.markdown("[Get Free API Key →](https://aistudio.google.com/app/apikey)", unsafe_allow_html=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**📱 Features**")
    st.markdown("""
    - 🍽️ **Nutrition Analysis** — Macros, micros, allergens
    - 🔬 **Freshness Detection** — Spoilage AI scanner
    - 🏥 **Kitchen Hygiene Audit** — FSSAI-style compliance
    """)

    st.markdown("---")
    st.markdown('<p style="color:#5a9b60;font-size:0.75rem;text-align:center;">Powered by Google Gemini 1.5 Flash</p>', unsafe_allow_html=True)


# ── Main App ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:1.5rem 0 0.5rem 0;">
    <h1 style="font-size:2.5rem;margin:0;">🥗 FoodVerse AI</h1>
    <p style="color:#9cb8a0;font-size:1.1rem;margin:0.3rem 0 0 0;">Multimodal Food Intelligence Platform · Nutrition · Freshness · Hygiene</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "🍽️ Nutrition Analyzer",
    "🔬 Freshness Detector",
    "🏥 Kitchen Hygiene Audit"
])

# ── TAB 1: NUTRITION ──────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Upload a food image for instant nutritional analysis")
    uploaded = st.file_uploader(
        "Drop your meal photo here",
        type=["jpg", "jpeg", "png", "webp"],
        key="nutrition_upload",
        label_visibility="collapsed",
    )
    if uploaded:
        image = Image.open(uploaded)
        col_img, col_btn = st.columns([3, 1])
        with col_img:
            st.image(image, caption="Uploaded Meal", use_container_width=True)
        with col_btn:
            analyze_btn = st.button("🔍 Analyze Nutrition", key="analyze_nutrition")

        if analyze_btn:
            model = get_gemini_model()
            if not model:
                st.error("⚠️ Please enter your Gemini API key in the sidebar first!")
            else:
                with st.spinner("🧠 Analyzing nutritional content..."):
                    data = analyze_nutrition(model, image)
                st.markdown("---")
                render_nutrition_results(data)
    else:
        st.markdown("""
        <div class="result-section" style="text-align:center;padding:3rem;">
            <p style="font-size:3rem;margin:0;">📸</p>
            <p style="font-size:1.1rem;margin:0.5rem 0;">Upload a photo of your meal to get instant nutrition facts</p>
            <p style="color:#5a9b60;font-size:0.9rem;">Supports: burgers, salads, rice dishes, snacks, beverages, and more</p>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 2: FRESHNESS ──────────────────────────────────────────────────────────
with tab2:
    st.markdown("### Upload a food or produce image to check freshness")
    uploaded_f = st.file_uploader(
        "Drop your food item photo here",
        type=["jpg", "jpeg", "png", "webp"],
        key="freshness_upload",
        label_visibility="collapsed",
    )
    if uploaded_f:
        image_f = Image.open(uploaded_f)
        col_img, col_btn = st.columns([3, 1])
        with col_img:
            st.image(image_f, caption="Food Item", use_container_width=True)
        with col_btn:
            fresh_btn = st.button("🔬 Check Freshness", key="analyze_freshness")

        if fresh_btn:
            model = get_gemini_model()
            if not model:
                st.error("⚠️ Please enter your Gemini API key in the sidebar first!")
            else:
                with st.spinner("🧪 Scanning for freshness indicators..."):
                    data_f = analyze_freshness(model, image_f)
                st.markdown("---")
                render_freshness_results(data_f)
    else:
        st.markdown("""
        <div class="result-section" style="text-align:center;padding:3rem;">
            <p style="font-size:3rem;margin:0;">🥦</p>
            <p style="font-size:1.1rem;margin:0.5rem 0;">Upload a photo of fruits, vegetables, meat, or any perishable food</p>
            <p style="color:#5a9b60;font-size:0.9rem;">AI will detect spoilage, estimate shelf life, and recommend storage</p>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 3: HYGIENE ────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Upload a kitchen or food prep area photo for hygiene audit")
    uploaded_h = st.file_uploader(
        "Drop your kitchen photo here",
        type=["jpg", "jpeg", "png", "webp"],
        key="hygiene_upload",
        label_visibility="collapsed",
    )
    if uploaded_h:
        image_h = Image.open(uploaded_h)
        col_img, col_btn = st.columns([3, 1])
        with col_img:
            st.image(image_h, caption="Kitchen Area", use_container_width=True)
        with col_btn:
            hygiene_btn = st.button("🏥 Run Hygiene Audit", key="analyze_hygiene")

        if hygiene_btn:
            model = get_gemini_model()
            if not model:
                st.error("⚠️ Please enter your Gemini API key in the sidebar first!")
            else:
                with st.spinner("🔍 Running hygiene compliance inspection..."):
                    data_h = analyze_hygiene(model, image_h)
                st.markdown("---")
                render_hygiene_results(data_h)
    else:
        st.markdown("""
        <div class="result-section" style="text-align:center;padding:3rem;">
            <p style="font-size:3rem;margin:0;">🍳</p>
            <p style="font-size:1.1rem;margin:0.5rem 0;">Upload a photo of your kitchen, storage area, or food preparation zone</p>
            <p style="color:#5a9b60;font-size:0.9rem;">Get an FSSAI-style hygiene score across cleanliness, storage, pest control & more</p>
        </div>
        """, unsafe_allow_html=True)
