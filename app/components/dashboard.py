"""
dashboard.py
-----------
Dashboard/Home page component.
"""

import streamlit as st


def render_dashboard():
    """Dashboard home page with enhanced navigation cards."""
    
    st.title("🏠 Welcome to The Agentic Auditor")
    st.markdown("**Streamline your utility billing analysis with AI-powered insights**")
    st.markdown("---")
    
    # Card definitions with enhanced content
    cards = [
        {
            "title": "📁 Upload & Ingest",
            "description": "Upload utility bills and tariff documents",
            "details": "Securely upload PDF files for processing and analysis",
            "page": "Upload & Ingest",
            "color": "#667eea",
            "icon": "📁"
        },
        {
            "title": "📄 Audit Bills",
            "description": "Review and validate billing information",
            "details": "Comprehensive audit of extracted billing data with anomaly detection",
            "page": "Audit Bills",
            "color": "#764ba2",
            "icon": "📄"
        },
        {
            "title": "📑 Manage Tariffs",
            "description": "Manage tariff structures and rates",
            "details": "View, organize, and manage utility tariff information",
            "page": "Manage Tariffs",
            "color": "#f093fb",
            "icon": "📑"
        },
        {
            "title": "📊 Pipeline Status",
            "description": "Monitor pipeline execution",
            "details": "Real-time tracking of processing jobs and execution logs",
            "page": "Pipeline Status",
            "color": "#00f2fe",
            "icon": "📊"
        },
        {
            "title": "📋 Generate Reports",
            "description": "Create detailed analysis reports",
            "details": "Generate comprehensive audit reports with visualizations",
            "page": "Generate Reports",
            "color": "#43e97b",
            "icon": "📋"
        },
        {
            "title": "📜 Upload History",
            "description": "View all uploaded documents",
            "details": "Track and manage your document upload history",
            "page": "Upload History",
            "color": "#fa709a",
            "icon": "📜"
        },
    ]
    
    # Custom CSS for enhanced cards with buttons inside
    st.markdown("""
        <style>
        .dashboard-card-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            margin: 20px 0;
        }
        
        /* Base button styling to match cards */
        div[data-testid=\"column\"] div.stButton > button {
            background: rgba(255, 255, 255, 0.25) !important;
            border: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 20px !important;
            padding: 8px 24px !important;
            color: white !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
            width: auto !important;
            margin: 0 auto !important;
            display: inline-block !important;
        }

        div[data-testid=\"column\"] div.stButton > button:hover {
            background: rgba(255, 255, 255, 0.35) !important;
            border-color: rgba(255, 255, 255, 0.8) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Display cards in a grid
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    for idx, card in enumerate(cards):
        col = cols[idx % 3]
        
        with col:
            # Inject dynamic gradient colors
            card_style = f"""
            <style>
            #card_{idx} {{
                --color-1: {card['color']};
                --color-2: {card['color']}dd;
            }}
            </style>
            """
            st.markdown(card_style, unsafe_allow_html=True)
            
            # Create clickable card with enhanced HTML styling
            card_id = f"card_{idx}"
            
            st.markdown(f"""
            <style>
            #{card_id} {{
                background: linear-gradient(135deg, {card['color']} 0%, {card['color']}cc 100%);
                padding: 0;
                margin: 0;
                border: none;
                border-radius: 18px;
                overflow: hidden;
                position: relative;
            }}
            
            #{card_id}:before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 100%);
                pointer-events: none;
            }}
            
            .card-wrapper-{idx} {{
                background: linear-gradient(135deg, {card['color']} 0%, {card['color']}aa 100%);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 18px;
                padding: 24px 20px 24px 20px;
                height: 300px;
                display: flex;
                flex-direction: column;
                box-shadow: 
                    0 10px 30px rgba(0, 0, 0, 0.3),
                    0 1px 8px rgba(0, 0, 0, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                cursor: default;
                position: relative;
                overflow: hidden;
            }}
            
            .card-wrapper-{idx}:hover {{
                transform: translateY(-10px) scale(1.02);
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.4),
                    0 5px 15px rgba(0, 0, 0, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            
            .card-wrapper-{idx}:before {{
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                bottom: -50%;
                left: -50%;
                background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
                opacity: 0;
                transition: opacity 0.4s ease;
            }}
            
            .card-wrapper-{idx}:hover:before {{
                opacity: 1;
            }}
            
            .card-icon-{idx} {{
                font-size: 48px;
                margin-bottom: 12px;
                filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
                animation: float-{idx} 3s ease-in-out infinite;
                height: 52px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            @keyframes float-{idx} {{
                0%, 100% {{ transform: translateY(0px); }}
                50% {{ transform: translateY(-8px); }}
            }}
            
            .card-title-{idx} {{
                font-size: 20px;
                font-weight: 800;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                color: white;
                min-height: 48px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .card-desc-{idx} {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 0;
                padding-bottom: 0;
                opacity: 0.95;
                line-height: 1.4;
                color: white;
                min-height: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .card-details-{idx} {{
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
                opacity: 0.9;
                border-top: 2px solid rgba(255,255,255,0.25);
                padding-top: 6px;
                margin-top: 0;
                margin-bottom: 0;
                color: white;
                min-height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            
            .card-button-{idx} {{
                background: rgba(255, 255, 255, 0.25);
                border: 2px solid rgba(255, 255, 255, 0.5);
                border-radius: 20px;
                padding: 8px 24px;
                color: white;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                cursor: pointer;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                display: inline-block;
                margin-top: 12px;
            }}
            
            .card-button-{idx}:hover {{
                background: rgba(255, 255, 255, 0.35);
                border-color: rgba(255, 255, 255, 0.8);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            }}
            
            </style>
            
            <div class="card-wrapper-{idx}" id="card-shell-{idx}">
                <div style="text-align: center; position: relative; z-index: 1; display: flex; flex-direction: column; height: 100%; justify-content: space-between;">
                    <div>
                        <div class="card-icon-{idx}">{card['icon']}</div>
                        <div class="card-title-{idx}">{card['title']}</div>
                        <div class="card-desc-{idx}">{card['description']}</div>
                    </div>
                    <div>
                        <div class="card-details-{idx}">{card['details']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Place the button inside the same container and pull it upward via CSS per card
            st.markdown(f"""
            <style>
            /* Position button for card {idx} */
            div[data-testid='column'] > div:has(#card-shell-{idx}) + div button {{
                position: relative !important;
                top: -38px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                display: inline-block !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            if st.button("Open →", key=f"card-btn-{idx}", use_container_width=False):
                st.session_state.nav_state = card["page"]
                st.rerun()

