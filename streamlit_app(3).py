from __future__ import annotations

import html
import math
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# App configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Market Lens 2.3｜市場透視",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The app has its own theme because most of the interface is custom HTML/CSS.
# Keeping it in session state makes the choice persist while the app is open.
if "light_mode" not in st.session_state:
    st.session_state["light_mode"] = False
LIGHT_MODE = bool(st.session_state["light_mode"])

st.markdown(
    """
    <style>
      :root {
        --ml-bg: #070b14;
        --ml-panel: rgba(17, 25, 42, .78);
        --ml-panel-strong: rgba(20, 30, 50, .96);
        --ml-border: rgba(147, 166, 199, .18);
        --ml-text: #f4f7fb;
        --ml-muted: #93a2ba;
        --ml-blue: #6ea8fe;
        --ml-cyan: #56d4dd;
        --ml-green: #55d69e;
        --ml-red: #ff7b91;
        --ml-amber: #ffc76a;
      }

      .stApp {
        background:
          radial-gradient(circle at 78% -10%, rgba(70, 105, 210, .18), transparent 31rem),
          radial-gradient(circle at 14% 18%, rgba(39, 185, 191, .08), transparent 25rem),
          linear-gradient(180deg, #080d18 0%, #070b14 100%);
        color: var(--ml-text);
      }
      header[data-testid="stHeader"] {background: rgba(7, 11, 20, .55); backdrop-filter: blur(14px);}
      .block-container {max-width: 1460px; padding-top: 1.35rem; padding-bottom: 4rem;}

      section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(14, 21, 36, .98), rgba(9, 14, 25, .98));
        border-right: 1px solid var(--ml-border);
      }
      section[data-testid="stSidebar"] .block-container {padding-top: 1.1rem;}
      section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 11px;
        padding: .48rem .60rem;
        margin: .10rem 0;
        transition: all .18s ease;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(110, 168, 254, .08);
      }

      h1, h2, h3 {letter-spacing: -.025em;}
      h1 {font-size: clamp(2rem, 4vw, 3.35rem) !important; line-height: 1.02 !important;}
      h2 {margin-top: 1.5rem !important;}
      p, li {line-height: 1.62;}

      .ml-brand {
        display: flex; align-items: center; gap: .72rem; margin: .15rem 0 .4rem;
      }
      .ml-logo {
        width: 38px; height: 38px; border-radius: 12px;
        display: grid; place-items: center; font-weight: 800; font-size: 18px;
        color: #06111c; background: linear-gradient(135deg, var(--ml-cyan), var(--ml-blue));
        box-shadow: 0 8px 28px rgba(83, 164, 240, .22);
      }
      .ml-brand-title {font-weight: 760; font-size: 1.08rem; letter-spacing: -.02em;}
      .ml-brand-sub {color: var(--ml-muted); font-size: .78rem; margin-top: -.1rem;}

      .ml-hero {
        position: relative; overflow: hidden;
        border: 1px solid var(--ml-border);
        border-radius: 24px;
        padding: clamp(1.35rem, 3vw, 2.35rem);
        margin-bottom: 1.25rem;
        background:
          radial-gradient(circle at 92% 15%, rgba(86, 212, 221, .14), transparent 17rem),
          linear-gradient(135deg, rgba(19, 30, 52, .96), rgba(10, 16, 28, .92));
        box-shadow: 0 22px 65px rgba(0, 0, 0, .22);
      }
      .ml-eyebrow {
        color: var(--ml-cyan); font-size: .75rem; font-weight: 800;
        letter-spacing: .16em; text-transform: uppercase; margin-bottom: .65rem;
      }
      .ml-hero-title {font-size: clamp(2rem, 4vw, 3.35rem); font-weight: 790; letter-spacing: -.045em; line-height: 1.02;}
      .ml-hero-sub {color: #afbdd0; font-size: 1.02rem; max-width: 780px; margin-top: .85rem;}
      .ml-chip-row {display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.05rem;}
      .ml-chip {
        display: inline-flex; align-items: center; gap: .35rem;
        border: 1px solid rgba(145, 166, 202, .20); border-radius: 999px;
        background: rgba(7, 12, 22, .38); padding: .38rem .68rem;
        color: #b7c5d8; font-size: .78rem;
      }

      .ml-section-label {
        color: var(--ml-muted); font-size: .75rem; font-weight: 800;
        letter-spacing: .12em; text-transform: uppercase; margin: 1.35rem 0 .55rem;
      }
      .ml-card {
        height: 100%; border: 1px solid var(--ml-border); border-radius: 18px;
        background: linear-gradient(180deg, rgba(20, 30, 49, .78), rgba(13, 20, 34, .76));
        padding: 1.05rem 1.08rem; box-shadow: 0 14px 36px rgba(0, 0, 0, .13);
      }
      .ml-card-title {color: #aab8ca; font-size: .78rem; font-weight: 680; letter-spacing: .02em;}
      .ml-card-value {font-size: 1.62rem; font-weight: 780; letter-spacing: -.035em; margin-top: .38rem;}
      .ml-card-meta {color: var(--ml-muted); font-size: .78rem; margin-top: .32rem;}
      .ml-pos {color: var(--ml-green);}
      .ml-neg {color: var(--ml-red);}
      .ml-neu {color: var(--ml-amber);}

      .ml-brief {
        border: 1px solid var(--ml-border); border-radius: 18px;
        padding: 1rem 1.1rem; margin: .62rem 0;
        background: rgba(13, 21, 36, .72);
      }
      .ml-brief-num {
        display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 8px;
        margin-right: .55rem; color: #07101b; font-weight: 800; font-size: .78rem;
        background: linear-gradient(135deg, var(--ml-cyan), var(--ml-blue));
      }
      .ml-muted {color: var(--ml-muted);}
      .ml-badge {
        display: inline-flex; align-items: center; border-radius: 999px; padding: .22rem .55rem;
        font-size: .70rem; font-weight: 760; letter-spacing: .035em;
        border: 1px solid rgba(145, 166, 202, .20); background: rgba(145, 166, 202, .08);
      }
      .ml-badge-green {color: var(--ml-green); border-color: rgba(85, 214, 158, .24); background: rgba(85, 214, 158, .08);}
      .ml-badge-red {color: var(--ml-red); border-color: rgba(255, 123, 145, .24); background: rgba(255, 123, 145, .08);}
      .ml-badge-amber {color: var(--ml-amber); border-color: rgba(255, 199, 106, .24); background: rgba(255, 199, 106, .08);}

      div[data-testid="stMetric"] {
        border: 1px solid var(--ml-border); border-radius: 16px;
        padding: .9rem 1rem; background: rgba(16, 25, 42, .72);
      }
      div[data-testid="stMetric"] label {color: var(--ml-muted) !important;}
      div[data-testid="stMetricValue"] {letter-spacing: -.035em;}
      div[data-testid="stDataFrame"], div[data-testid="stTable"] {
        border: 1px solid var(--ml-border); border-radius: 16px; overflow: hidden;
      }
      div[data-testid="stExpander"] {
        border: 1px solid var(--ml-border); border-radius: 14px; background: rgba(14, 22, 37, .58);
      }
      button[kind="primary"] {
        background: linear-gradient(135deg, #4f7ef4, #4dcbd2) !important;
        border: 0 !important; color: #07101b !important; font-weight: 760 !important;
      }
      .stTabs [data-baseweb="tab-list"] {gap: .45rem;}
      .stTabs [data-baseweb="tab"] {
        border: 1px solid var(--ml-border); border-radius: 999px; padding: .45rem .85rem;
        background: rgba(17, 26, 43, .64);
      }
      .stTabs [aria-selected="true"] {background: rgba(91, 149, 244, .16) !important;}
      [data-testid="stFileUploader"] {border-radius: 16px;}
      .ml-footer {color: #6f8099; font-size: .73rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--ml-border);}

      @media (max-width: 760px) {
        .block-container {padding-left: 1rem; padding-right: 1rem;}
        .ml-hero {border-radius: 19px; padding: 1.25rem;}
        .ml-card-value {font-size: 1.35rem;}
      }

      /* Market Lens 2.2 — premium terminal polish */
      html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      #MainMenu, footer, [data-testid="stStatusWidget"] {
        visibility: hidden;
      }
      /* Keep both sidebar controls accessible. Hiding the full Streamlit toolbar can
         also hide the reopen button after the sidebar is collapsed. */
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 1000000 !important;
      }
      [data-testid="stSidebarCollapsedControl"] {
        position: fixed !important;
        top: .58rem !important;
        left: .62rem !important;
      }
      [data-testid="stSidebarCollapsedControl"] button,
      [data-testid="stSidebarCollapseButton"] button {
        border: 1px solid rgba(145, 166, 202, .22) !important;
        border-radius: 10px !important;
        background: rgba(15, 23, 39, .88) !important;
        color: #eaf1fb !important;
        box-shadow: 0 8px 24px rgba(0,0,0,.18) !important;
      }
      [data-testid="stToolbar"] {
        visibility: visible !important;
      }
      header[data-testid="stHeader"] {
        height: 2.55rem;
        background: rgba(7, 11, 20, .72);
        border-bottom: 1px solid rgba(147, 166, 199, .07);
      }
      .block-container {
        max-width: 1400px;
        padding-top: 2rem;
      }
      section[data-testid="stSidebar"] {
        min-width: 264px;
        max-width: 264px;
        box-shadow: 18px 0 50px rgba(0, 0, 0, .16);
      }
      section[data-testid="stSidebar"] .block-container {
        padding: 1.25rem .9rem 1.25rem;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: .26rem;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        border: 1px solid transparent;
        border-radius: 12px;
        padding: .64rem .68rem;
        margin: 0;
        color: #b9c5d6;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(90deg, rgba(104, 183, 255, .16), rgba(86, 212, 221, .06));
        border-color: rgba(104, 183, 255, .24);
        color: #f6f9ff;
        box-shadow: inset 3px 0 0 #68b7ff;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        font-weight: 700;
      }
      .ml-brand {
        padding: .45rem .35rem .85rem;
        margin-bottom: .2rem;
      }
      .ml-logo {
        width: 42px;
        height: 42px;
        border-radius: 13px;
        background: linear-gradient(145deg, #86e8e6 0%, #75a8ff 58%, #8d7cff 100%);
        box-shadow: 0 10px 34px rgba(104, 183, 255, .25), inset 0 1px rgba(255,255,255,.42);
      }
      .ml-brand-title {font-size: 1rem; letter-spacing: -.025em;}
      .ml-version {
        display:inline-flex; margin-left:.35rem; padding:.12rem .35rem; border-radius:999px;
        background:rgba(104,183,255,.12); color:#8bc8ff; font-size:.62rem; vertical-align:middle;
        border:1px solid rgba(104,183,255,.18);
      }
      .ml-hero {
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        border-radius: 28px;
        padding: 2.25rem 2.35rem;
        background:
          radial-gradient(circle at 86% 22%, rgba(98, 213, 220, .20), transparent 17rem),
          radial-gradient(circle at 66% 125%, rgba(111, 121, 255, .20), transparent 22rem),
          linear-gradient(135deg, rgba(20, 31, 54, .98), rgba(9, 15, 27, .97));
        border-color: rgba(135, 166, 216, .22);
        box-shadow: 0 28px 80px rgba(0, 0, 0, .28), inset 0 1px rgba(255,255,255,.035);
      }
      .ml-hero::after {
        content: "ML";
        position: absolute;
        right: 2.2rem;
        top: 1.15rem;
        font-size: 7.8rem;
        font-weight: 900;
        letter-spacing: -.09em;
        color: rgba(255,255,255,.025);
        pointer-events: none;
      }
      .ml-hero-title {
        max-width: 920px;
        font-size: clamp(2.15rem, 4.2vw, 3.55rem);
        text-wrap: balance;
      }
      .ml-hero-sub {max-width: 800px; color:#b7c3d4;}
      .ml-chip {
        background: rgba(6, 12, 23, .48);
        border-color: rgba(155, 179, 217, .18);
        backdrop-filter: blur(8px);
      }
      .ml-section-label {
        display:flex;
        align-items:center;
        gap:.8rem;
        margin: 1.75rem 0 .72rem;
        color:#8ea0b9;
      }
      .ml-section-label::after {
        content:"";
        height:1px;
        flex:1;
        background:linear-gradient(90deg, rgba(145,166,202,.20), transparent);
      }
      .ml-card {
        border-radius: 19px;
        background: linear-gradient(180deg, rgba(20, 30, 49, .86), rgba(12, 19, 32, .84));
        border-color: rgba(145, 166, 202, .17);
        box-shadow: 0 13px 34px rgba(0,0,0,.16), inset 0 1px rgba(255,255,255,.025);
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
      }
      .ml-card:hover {
        transform: translateY(-2px);
        border-color: rgba(104,183,255,.30);
        box-shadow: 0 18px 44px rgba(0,0,0,.22);
      }
      .ml-card-title {letter-spacing:.06em; text-transform:uppercase; font-size:.68rem;}
      .ml-card-value {font-size: 1.72rem;}
      .ml-brief {
        position:relative;
        border-radius:17px;
        background:linear-gradient(90deg, rgba(19,29,48,.82), rgba(12,19,32,.70));
        border-color:rgba(145,166,202,.15);
        padding:1.05rem 1.15rem;
      }
      .ml-brief:hover {border-color:rgba(104,183,255,.28);}
      .ml-brief-num {background:linear-gradient(135deg,#86e8e6,#75a8ff);}

      .ml-tape {
        overflow:hidden;
        border:1px solid rgba(145,166,202,.16);
        border-radius:20px;
        background:rgba(10,16,27,.60);
        box-shadow:0 18px 48px rgba(0,0,0,.16);
      }
      .ml-tape-row {
        display:grid;
        grid-template-columns: 1.15fr 1.55fr 1fr .95fr .8fr .8fr .8fr;
        align-items:center;
        min-height:48px;
        padding:0 .9rem;
        border-bottom:1px solid rgba(145,166,202,.09);
        gap:.7rem;
      }
      .ml-tape-row:last-child {border-bottom:0;}
      .ml-tape-row:not(.ml-tape-head):hover {background:rgba(104,183,255,.045);}
      .ml-tape-head {
        min-height:42px;
        background:rgba(255,255,255,.025);
        color:#75869f;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.09em;
        text-transform:uppercase;
      }
      .ml-tape-name {font-weight:680;color:#e8edf6;}
      .ml-tape-symbol {font-family:"SFMono-Regular",Consolas,monospace;color:#7e91aa;font-size:.78rem;}
      .ml-tape-number {text-align:right;font-variant-numeric:tabular-nums;font-family:"SFMono-Regular",Consolas,monospace;}
      .ml-asset-pill {
        width:max-content; padding:.22rem .48rem; border-radius:999px;
        background:rgba(145,166,202,.075); border:1px solid rgba(145,166,202,.12);
        color:#a8b6c9; font-size:.68rem; font-weight:700;
      }
      .ml-move {
        display:inline-flex; justify-content:flex-end; min-width:58px;
        padding:.20rem .38rem; border-radius:7px; font-size:.76rem; font-weight:700;
      }
      .ml-move-pos {color:#62d9a4;background:rgba(85,214,158,.075);}
      .ml-move-neg {color:#ff8498;background:rgba(255,123,145,.075);}
      .ml-move-flat {color:#d8b66e;background:rgba(255,199,106,.065);}

      .ml-cb-card {
        height:100%; min-height:172px; padding:1.2rem 1.25rem 1.05rem;
        border:1px solid rgba(145,166,202,.16); border-radius:20px;
        background:linear-gradient(165deg, rgba(21,31,51,.90), rgba(11,18,31,.87));
        box-shadow:0 15px 38px rgba(0,0,0,.17); position:relative; overflow:hidden;
      }
      .ml-cb-card::before {
        content:""; position:absolute; left:0; top:0; width:100%; height:2px;
        background:linear-gradient(90deg,#68b7ff,#56d4dd,transparent 75%);
      }
      .ml-cb-name {color:#8eb6ef;font-size:.73rem;font-weight:800;letter-spacing:.04em;}
      .ml-cb-rate {font-size:1.72rem;font-weight:800;letter-spacing:-.04em;margin:.55rem 0 .28rem;}
      .ml-cb-meta {color:#90a0b7;font-size:.78rem;line-height:1.48;min-height:40px;}
      .ml-cb-link {
        display:inline-flex; align-items:center; gap:.35rem; margin-top:.85rem;
        color:#9bcfff !important; text-decoration:none !important; font-size:.76rem; font-weight:700;
      }
      .ml-cb-link:hover {color:#d7efff !important;}
      .ml-discipline {
        display:flex; flex-wrap:wrap; align-items:center; gap:.55rem;
        padding:.82rem 1rem; margin-top:1rem; border-radius:14px;
        border:1px solid rgba(104,183,255,.16);
        background:linear-gradient(90deg,rgba(56,119,184,.20),rgba(27,69,105,.13));
        color:#9fcfff; font-size:.79rem;
      }
      .ml-step {display:inline-flex;align-items:center;gap:.38rem;}
      .ml-step b {color:#eef7ff;}
      .ml-arrow {color:#4f7299;}

      @media (max-width: 900px) {
        .ml-tape-head {display:none;}
        .ml-tape-row {grid-template-columns:1fr 1fr 1fr; padding:.75rem .8rem; gap:.4rem .65rem;}
        .ml-tape-row > :nth-child(3), .ml-tape-row > :nth-child(6), .ml-tape-row > :nth-child(7) {display:none;}
        .ml-tape-number {text-align:right;}
        section[data-testid="stSidebar"] {min-width:240px;max-width:240px;}
      }
      @media (max-width: 760px) {
        header[data-testid="stHeader"] {height:2rem;}
        .block-container {padding-top:1.2rem;}
        .ml-hero {min-height:auto;padding:1.45rem 1.25rem;border-radius:22px;}
        .ml-hero::after {font-size:4.5rem;right:1rem;top:.7rem;}
        .ml-section-label {margin-top:1.35rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# Light-mode overrides. Streamlit's built-in theme switch cannot recolour custom
# HTML cards reliably, so the dashboard exposes a native in-app toggle instead.
if LIGHT_MODE:
    st.markdown(
        """
        <style>
          :root {
            --ml-bg: #f4f7fb;
            --ml-panel: rgba(255, 255, 255, .90);
            --ml-panel-strong: rgba(255, 255, 255, .98);
            --ml-border: rgba(42, 64, 98, .14);
            --ml-text: #142038;
            --ml-muted: #61718a;
            --ml-blue: #316fe8;
            --ml-cyan: #168f9b;
            --ml-green: #087b52;
            --ml-red: #c73e5a;
            --ml-amber: #9a6400;
          }

          html, body, .stApp, [data-testid="stAppViewContainer"] {
            color: var(--ml-text) !important;
            background: #f4f7fb !important;
          }
          .stApp {
            background:
              radial-gradient(circle at 80% -12%, rgba(80, 126, 238, .13), transparent 32rem),
              radial-gradient(circle at 12% 20%, rgba(33, 176, 184, .08), transparent 26rem),
              linear-gradient(180deg, #f7f9fc 0%, #eef3f9 100%) !important;
          }
          header[data-testid="stHeader"] {
            background: rgba(247, 249, 252, .82) !important;
            border-bottom-color: rgba(42,64,98,.08) !important;
          }
          section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(244,247,252,.98)) !important;
            border-right-color: rgba(42,64,98,.13) !important;
            box-shadow: 18px 0 50px rgba(45,65,96,.07) !important;
          }
          .stApp h1, .stApp h2, .stApp h3, .stApp h4,
          .stApp p, .stApp li, .stApp label,
          section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] label {
            color: var(--ml-text);
          }
          .ml-brand-title {color:#17243b;}
          .ml-brand-sub, .ml-muted, .ml-card-meta, .ml-section-label {color:#66768e !important;}
          .ml-version {background:rgba(49,111,232,.10);color:#2e68d5;border-color:rgba(49,111,232,.18);}

          section[data-testid="stSidebar"] [data-testid="stRadio"] label {color:#40516b;}
          section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:rgba(49,111,232,.055);}
          section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            color:#10213d !important;
            background:linear-gradient(90deg, rgba(49,111,232,.12), rgba(22,143,155,.055)) !important;
            border-color:rgba(49,111,232,.18) !important;
            box-shadow:inset 3px 0 0 #316fe8 !important;
          }

          .ml-hero {
            background:
              radial-gradient(circle at 87% 18%, rgba(40, 166, 174, .13), transparent 18rem),
              radial-gradient(circle at 65% 125%, rgba(82, 101, 226, .11), transparent 22rem),
              linear-gradient(135deg, rgba(255,255,255,.98), rgba(239,245,255,.96)) !important;
            border-color:rgba(55,91,145,.17) !important;
            box-shadow:0 24px 65px rgba(60,82,118,.12), inset 0 1px rgba(255,255,255,.8) !important;
          }
          .ml-hero-title {color:#12213b !important;}
          .ml-hero-sub {color:#526681 !important;}
          .ml-hero::after {color:rgba(25,57,103,.035) !important;}
          .ml-eyebrow {color:#087f8b !important;}
          .ml-chip {background:rgba(255,255,255,.68) !important;border-color:rgba(42,64,98,.14) !important;color:#4d607a !important;}

          .ml-card, div[data-testid="stMetric"], .ml-brief, div[data-testid="stExpander"] {
            background:linear-gradient(180deg, rgba(255,255,255,.96), rgba(247,250,254,.91)) !important;
            border-color:rgba(42,64,98,.13) !important;
            box-shadow:0 12px 30px rgba(55,76,108,.075) !important;
          }
          .ml-card:hover, .ml-brief:hover {border-color:rgba(49,111,232,.26) !important;box-shadow:0 16px 36px rgba(55,76,108,.11) !important;}
          .ml-card-title {color:#60728c !important;}
          .ml-card-value {color:#142038 !important;}
          .ml-brief {background:linear-gradient(90deg, rgba(255,255,255,.98), rgba(244,248,253,.92)) !important;}
          .ml-badge {background:rgba(57,76,107,.055);border-color:rgba(57,76,107,.13);}
          .ml-badge-green {color:#087b52 !important;background:rgba(8,123,82,.07) !important;border-color:rgba(8,123,82,.17) !important;}
          .ml-badge-red {color:#c73e5a !important;background:rgba(199,62,90,.065) !important;border-color:rgba(199,62,90,.16) !important;}
          .ml-badge-amber {color:#926000 !important;background:rgba(154,100,0,.065) !important;border-color:rgba(154,100,0,.16) !important;}
          .ml-pos {color:#087b52 !important;}.ml-neg {color:#c73e5a !important;}.ml-neu {color:#926000 !important;}

          .ml-tape {background:rgba(255,255,255,.88) !important;border-color:rgba(42,64,98,.13) !important;box-shadow:0 16px 38px rgba(55,76,108,.08) !important;}
          .ml-tape-row {border-bottom-color:rgba(42,64,98,.075) !important;}
          .ml-tape-row:not(.ml-tape-head):hover {background:rgba(49,111,232,.035) !important;}
          .ml-tape-head {background:rgba(31,55,90,.035) !important;color:#71819a !important;}
          .ml-tape-name {color:#1b2940 !important;}.ml-tape-symbol {color:#6a7b94 !important;}
          .ml-asset-pill {background:rgba(49,72,106,.055) !important;border-color:rgba(49,72,106,.11) !important;color:#586b84 !important;}
          .ml-move-pos {color:#087b52 !important;background:rgba(8,123,82,.07) !important;}
          .ml-move-neg {color:#c73e5a !important;background:rgba(199,62,90,.065) !important;}
          .ml-move-flat {color:#926000 !important;background:rgba(154,100,0,.06) !important;}

          .ml-cb-card {
            background:linear-gradient(165deg, rgba(255,255,255,.98), rgba(242,247,254,.94)) !important;
            border-color:rgba(42,64,98,.13) !important;
            box-shadow:0 14px 34px rgba(55,76,108,.08) !important;
          }
          .ml-cb-name {color:#3268b8 !important;}.ml-cb-rate {color:#15243c !important;}.ml-cb-meta {color:#63748c !important;}
          .ml-cb-meta b {color:#253650 !important;}.ml-cb-link {color:#2361bd !important;}
          .ml-discipline {background:linear-gradient(90deg,rgba(49,111,232,.09),rgba(22,143,155,.055)) !important;border-color:rgba(49,111,232,.14) !important;color:#2b5fae !important;}
          .ml-step b {color:#153460 !important;}.ml-arrow {color:#7890ad !important;}

          .stTabs [data-baseweb="tab"] {background:rgba(255,255,255,.78) !important;border-color:rgba(42,64,98,.13) !important;color:#40516b !important;}
          .stTabs [aria-selected="true"] {background:rgba(49,111,232,.10) !important;color:#17345f !important;}
          div[data-testid="stDataFrame"], div[data-testid="stTable"] {border-color:rgba(42,64,98,.13) !important;}
          [data-baseweb="select"] > div,
          [data-baseweb="input"] > div,
          [data-baseweb="textarea"] > div,
          input, textarea {
            background-color:rgba(255,255,255,.92) !important;
            color:#142038 !important;
            border-color:rgba(42,64,98,.15) !important;
          }
          [data-testid="stSidebarCollapsedControl"] button,
          [data-testid="stSidebarCollapseButton"] button {
            background:rgba(255,255,255,.93) !important;
            color:#1d2b43 !important;
            border-color:rgba(42,64,98,.17) !important;
            box-shadow:0 8px 24px rgba(55,76,108,.12) !important;
          }
          [data-testid="stToolbar"] button {color:#283850 !important;}
          .ml-footer {color:#718099 !important;border-top-color:rgba(42,64,98,.12) !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Data dictionaries
# -----------------------------------------------------------------------------
MARKETS: dict[str, dict[str, str]] = {
    "^GSPC": {"name": "S&P 500", "group": "Equity"},
    "^IXIC": {"name": "Nasdaq", "group": "Equity"},
    "^SOX": {"name": "Semiconductors", "group": "Equity"},
    "^VIX": {"name": "VIX", "group": "Risk"},
    "^TNX": {"name": "US 10Y yield", "group": "Rates"},
    "DX-Y.NYB": {"name": "US Dollar Index", "group": "FX"},
    "GBPUSD=X": {"name": "GBP/USD", "group": "FX"},
    "CL=F": {"name": "WTI oil", "group": "Commodities"},
    "NG=F": {"name": "US natural gas", "group": "Commodities"},
    "GC=F": {"name": "Gold", "group": "Commodities"},
}

WATCHLIST: dict[str, dict[str, Any]] = {
    "APLD": {
        "name": "Applied Digital",
        "layer": "Data-centre capacity",
        "driver": "Lease execution, funding, construction, power and tenant quality",
        "bull": "Contracted capacity converts into durable cash flow without excessive dilution.",
        "risk": "Construction delays, financing cost, customer concentration and execution risk.",
        "disconfirm": "Repeated schedule slippage, weaker lease economics or materially higher funding needs.",
        "keywords": ["applied digital", "data center lease", "data centre lease"],
    },
    "MU": {
        "name": "Micron",
        "layer": "Memory / HBM",
        "driver": "HBM demand, DRAM pricing, supply discipline, yields and gross margin",
        "bull": "AI server demand sustains a tighter memory cycle and higher-value product mix.",
        "risk": "Memory remains cyclical; supply additions or demand digestion can compress pricing.",
        "disconfirm": "HBM qualification delays, weaker pricing or rapid industry capacity expansion.",
        "keywords": ["micron", "hbm", "dram", "memory chip"],
    },
    "NBIS": {
        "name": "Nebius",
        "layer": "AI cloud",
        "driver": "GPU supply, utilisation, customer ramp, CapEx, funding and unit economics",
        "bull": "Scarce AI compute supports high utilisation and rapid revenue scaling.",
        "risk": "Capital intensity, customer concentration, price competition and execution.",
        "disconfirm": "Utilisation stalls, contracted demand weakens or funding rises faster than capacity value.",
        "keywords": ["nebius", "ai cloud", "gpu cloud"],
    },
    "BE": {
        "name": "Bloom Energy",
        "layer": "On-site power",
        "driver": "Data-centre power demand, backlog conversion, gas economics and margins",
        "bull": "Grid constraints make fast, behind-the-meter power increasingly valuable.",
        "risk": "Project timing, fuel economics, policy changes and manufacturing execution.",
        "disconfirm": "Backlog fails to convert, margins deteriorate or customers choose cheaper alternatives.",
        "keywords": ["bloom energy", "fuel cell", "data center power", "data centre power"],
    },
    "TE": {
        "name": "T1 Energy",
        "layer": "Solar manufacturing",
        "driver": "US industrial policy, tariffs, factory ramp, customer contracts and financing",
        "bull": "Domestic supply-chain policy supports strategic manufacturing capacity.",
        "risk": "Policy reversal, factory execution, commodity pricing and financing.",
        "disconfirm": "Ramp targets slip, support weakens or contracted economics deteriorate.",
        "keywords": ["t1 energy", "solar manufacturing", "solar factory"],
    },
    "GOOGL": {
        "name": "Alphabet",
        "layer": "Hyperscaler demand",
        "driver": "Cloud growth, AI monetisation, search resilience and CapEx returns",
        "bull": "AI strengthens cloud and product monetisation while sustaining infrastructure demand.",
        "risk": "CapEx outruns monetisation, search disruption and regulatory pressure.",
        "disconfirm": "Cloud growth weakens while depreciation and infrastructure costs accelerate.",
        "keywords": ["alphabet", "google cloud", "google capex", "gemini"],
    },
    "MSFT": {
        "name": "Microsoft",
        "layer": "Hyperscaler demand",
        "driver": "Azure growth, AI utilisation, Copilot monetisation and CapEx returns",
        "bull": "Enterprise distribution converts AI infrastructure investment into recurring revenue.",
        "risk": "Capacity costs, slower monetisation and competition.",
        "disconfirm": "AI contribution slows while CapEx and depreciation continue to accelerate.",
        "keywords": ["microsoft", "azure", "copilot", "microsoft capex"],
    },
}

FRED_SERIES: dict[str, dict[str, str]] = {
    "DFF": {"name": "Effective federal funds rate", "short": "Fed funds", "transform": "raw", "unit": "%", "change": "bp", "frequency": "Daily"},
    "DGS2": {"name": "US 2-year Treasury yield", "short": "US 2Y", "transform": "raw", "unit": "%", "change": "bp", "frequency": "Daily"},
    "DGS10": {"name": "US 10-year Treasury yield", "short": "US 10Y", "transform": "raw", "unit": "%", "change": "bp", "frequency": "Daily"},
    "T10Y2": {"name": "10Y–2Y Treasury spread", "short": "10Y–2Y curve", "transform": "raw", "unit": "pp", "change": "bp", "frequency": "Daily"},
    "DFII10": {"name": "US 10-year real yield", "short": "10Y real yield", "transform": "raw", "unit": "%", "change": "bp", "frequency": "Daily"},
    "BAMLH0A0HYM2": {"name": "US high-yield option-adjusted spread", "short": "HY spread", "transform": "raw", "unit": "%", "change": "bp", "frequency": "Daily"},
    "CPIAUCSL": {"name": "US headline CPI — year-on-year", "short": "Headline CPI", "transform": "yoy", "unit": "% YoY", "change": "pp", "frequency": "Monthly"},
    "CPILFESL": {"name": "US core CPI — year-on-year", "short": "Core CPI", "transform": "yoy", "unit": "% YoY", "change": "pp", "frequency": "Monthly"},
    "PCEPILFE": {"name": "US core PCE — year-on-year", "short": "Core PCE", "transform": "yoy", "unit": "% YoY", "change": "pp", "frequency": "Monthly"},
    "UNRATE": {"name": "US unemployment rate", "short": "Unemployment", "transform": "raw", "unit": "%", "change": "pp", "frequency": "Monthly"},
    "PAYEMS": {"name": "US nonfarm payroll employment — year-on-year", "short": "Payroll growth", "transform": "yoy", "unit": "% YoY", "change": "pp", "frequency": "Monthly"},
    "ICSA": {"name": "Initial unemployment claims", "short": "Initial claims", "transform": "thousands", "unit": "thousand", "change": "percent", "frequency": "Weekly"},
    "JTSJOL": {"name": "US job openings", "short": "Job openings", "transform": "raw", "unit": "thousand", "change": "percent", "frequency": "Monthly"},
    "A191RL1Q225SBEA": {"name": "US real GDP growth", "short": "Real GDP", "transform": "raw", "unit": "% annualised", "change": "pp", "frequency": "Quarterly"},
}

TOPICS: dict[str, tuple[str, str, str, str]] = {
    "Yield curve": (
        "不同期限國債收益率的排列。2年期較敏感於央行路徑，10年期同時反映增長、通脹與期限溢價。",
        "2Y、10Y、10Y–2Y、實質利率 Real Yield、期限溢價 Term Premium。",
        "長端收益率上升 → 折現率提高 → 遠期盈利型資產估值通常受壓。",
        "把所有收益率上升都視為同一原因，而不拆分增長、通脹與期限溢價。",
    ),
    "Inflation surprise": (
        "市場短期交易的往往不是通脹絕對水平，而是 Actual 相對 Consensus 的差異。",
        "核心服務、住房、工資、能源、三個月年化趨勢與市場預期。",
        "高於預期 → 減息預期後移 → 短端收益率與美元可能上升。",
        "看到同比下降就直接判斷利好，忽略市場原本預期下降得更多。",
    ),
    "Credit spread": (
        "企業債相對國債的額外收益率補償，反映違約、流動性與風險偏好。",
        "高收益債利差、投資級利差、銀行貸款標準與再融資牆。",
        "利差擴大 → 融資成本上升 → 高負債、高CapEx公司壓力增加。",
        "只看無風險利率，忽略信用溢價也會大幅改變企業資金成本。",
    ),
    "AI CapEx cycle": (
        "大型科技公司擴建GPU、網絡、數據中心與電力基礎設施的資本開支周期。",
        "CapEx guidance、交付期、利用率、電力、供應鏈、折舊與投資回報。",
        "CapEx上調 → 上游訂單受惠；但若回報不足，後期可能削減並造成供應過剩。",
        "把今天的供不應求永久外推，忽略建設延遲與供給最終會追上。",
    ),
    "Earnings vs cash flow": (
        "盈利採用權責發生制；現金流則顯示企業實際收付款與資本投入。",
        "營運現金流、CapEx、自由現金流、應收帳、股票薪酬和融資需求。",
        "收入增長但CapEx增長更快 → FCF可能受壓 → 需要評估外部融資與回報率。",
        "只看EPS beat，忽略盈利質量、營運資金和現金消耗。",
    ),
    "FX transmission": (
        "匯率由相對利差、增長差、避險需求、貿易與資本流共同驅動。",
        "央行分歧、實質利率、美元流動性、商品價格與政治風險。",
        "美元上升 → 全球金融條件偏緊；英鎊投資者的美元資產換算回報可能增加。",
        "只看股票美元回報，忘記自己的實際回報以英鎊計算。",
    ),
}

SHOCKS: dict[str, list[tuple[str, str, str]]] = {
    "AI資本開支上調": [
        ("GPU／HBM／網絡設備", "需求與訂單可見度改善", "高"),
        ("數據中心容量", "租賃與建設需求增加", "高"),
        ("電力與併網", "瓶頸可能進一步加劇", "高"),
        ("大型科技自由現金流", "短期可能受壓", "中"),
        ("中期供應過剩風險", "亦會隨投資增加", "中"),
    ],
    "信用利差擴大": [
        ("高CapEx公司", "再融資與估值壓力上升", "高"),
        ("企業債", "價格受壓", "高"),
        ("銀行貸款標準", "通常趨緊", "中"),
        ("防禦性資產", "相對受惠", "中"),
    ],
    "通脹低於預期": [
        ("減息預期", "可能提前", "中高"),
        ("短端收益率", "通常下降", "高"),
        ("美元", "可能轉弱", "中"),
        ("長久期成長股", "折現率壓力下降", "中高"),
    ],
    "油價急升": [
        ("通脹預期", "上升", "高"),
        ("減息預期", "可能後移", "中高"),
        ("能源生產商", "相對受惠", "中"),
        ("消費者可支配收入", "受壓", "中"),
    ],
    "美元急升": [
        ("全球流動性", "收緊", "中高"),
        ("非美貨幣", "承壓", "高"),
        ("英鎊投資者持有美元資產", "換算回報增加", "高"),
        ("新興市場美元債務", "壓力上升", "高"),
    ],
}

NEWS_PRESETS: dict[str, str] = {
    "AI Infrastructure": '(AI OR "data center" OR "data centre" OR GPU OR HBM OR cloud OR semiconductor)',
    "Central Banks & Inflation": '(Federal Reserve OR ECB OR "Bank of England" OR inflation OR interest rates)',
    "FX & Liquidity": '(dollar OR sterling OR euro OR yen OR currency OR liquidity)',
    "Energy & Power": '(electricity OR power grid OR natural gas OR nuclear OR oil OR energy)',
    "Geopolitics & Trade": '(tariff OR sanctions OR export controls OR conflict OR trade policy)',
}

RANGE_DAYS = {"1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5, "10Y": 365 * 10}
MARKET_PERIODS = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}


# -----------------------------------------------------------------------------
# Utility and presentation helpers
# -----------------------------------------------------------------------------
def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
        return None if math.isnan(result) else result
    except (TypeError, ValueError):
        return None


def esc(value: Any) -> str:
    return html.escape(str(value))


def fmt_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def fmt_pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def delta_class(value: float | None) -> str:
    if value is None or abs(value) < 1e-12:
        return "ml-neu"
    return "ml-pos" if value > 0 else "ml-neg"


def hero(eyebrow: str, title: str, subtitle: str, chips: list[str] | None = None) -> None:
    chip_html = "".join(f'<span class="ml-chip">{esc(chip)}</span>' for chip in (chips or []))
    st.markdown(
        f"""
        <div class="ml-hero">
          <div class="ml-eyebrow">{esc(eyebrow)}</div>
          <div class="ml-hero-title">{esc(title)}</div>
          <div class="ml-hero-sub">{esc(subtitle)}</div>
          <div class="ml-chip-row">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="ml-section-label">{esc(text)}</div>', unsafe_allow_html=True)


def stat_card(title: str, value: str, delta: str = "", meta: str = "", css_class: str = "ml-neu") -> None:
    delta_html = f'<span class="{css_class}">{esc(delta)}</span>' if delta else ""
    st.markdown(
        f"""
        <div class="ml-card">
          <div class="ml-card-title">{esc(title)}</div>
          <div class="ml-card-value">{esc(value)}</div>
          <div class="ml-card-meta">{delta_html}{' · ' if delta and meta else ''}{esc(meta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def brief_card(number: int, title: str, body: str) -> None:
    st.markdown(
        f'<div class="ml-brief"><span class="ml-brief-num">{number}</span><b>{esc(title)}</b><div class="ml-muted" style="margin:.45rem 0 0 2.45rem">{esc(body)}</div></div>',
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "neutral") -> str:
    css = {"green": "ml-badge-green", "red": "ml-badge-red", "amber": "ml-badge-amber"}.get(kind, "")
    return f'<span class="ml-badge {css}">{esc(text)}</span>'


def move_pill(value: float | None) -> str:
    if value is None:
        return '<span class="ml-move ml-move-flat">—</span>'
    css = "ml-move-pos" if value > 0 else "ml-move-neg" if value < 0 else "ml-move-flat"
    return f'<span class="ml-move {css}">{value:+.2f}%</span>'


def market_tape_html(frame: pd.DataFrame) -> str:
    rows = [
        '<div class="ml-tape-row ml-tape-head"><div>Asset</div><div>Name</div><div>Ticker</div><div style="text-align:right">Last</div><div style="text-align:right">1D</div><div style="text-align:right">5D</div><div style="text-align:right">1M</div></div>'
    ]
    for _, row in frame.iterrows():
        ticker = str(row["Ticker"])
        asset_class = MARKETS.get(ticker, {}).get("group", "Other")
        last = safe_float(row.get("Last"))
        one_day = safe_float(row.get("1D %"))
        five_day = safe_float(row.get("5D %"))
        one_month = safe_float(row.get("1M %"))
        rows.append(
            f'''<div class="ml-tape-row">
                <div><span class="ml-asset-pill">{esc(asset_class)}</span></div>
                <div class="ml-tape-name">{esc(row.get("Name", ticker))}</div>
                <div class="ml-tape-symbol">{esc(ticker)}</div>
                <div class="ml-tape-number">{fmt_number(last)}</div>
                <div class="ml-tape-number">{move_pill(one_day)}</div>
                <div class="ml-tape-number">{move_pill(five_day)}</div>
                <div class="ml-tape-number">{move_pill(one_month)}</div>
              </div>'''
        )
    return '<div class="ml-tape">' + ''.join(rows) + '</div>'


def central_bank_card(name: str, value: str, label: str, context: str, url: str) -> None:
    st.markdown(
        f'''<div class="ml-cb-card">
              <div class="ml-cb-name">{esc(name)}</div>
              <div class="ml-cb-rate">{esc(value)}</div>
              <div class="ml-cb-meta"><b>{esc(label)}</b> · {esc(context)}</div>
              <a class="ml-cb-link" href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open primary source <span>↗</span></a>
            </div>''',
        unsafe_allow_html=True,
    )


def discipline_strip() -> None:
    st.markdown(
        '''<div class="ml-discipline">
             <span style="font-weight:800;color:#72c7ff;margin-right:.15rem">DAILY DISCIPLINE</span>
             <span class="ml-step"><b>1</b> Price action</span><span class="ml-arrow">→</span>
             <span class="ml-step"><b>2</b> Macro driver</span><span class="ml-arrow">→</span>
             <span class="ml-step"><b>3</b> Primary source</span><span class="ml-arrow">→</span>
             <span class="ml-step"><b>4</b> Portfolio exposure</span><span class="ml-arrow">→</span>
             <span class="ml-step"><b>5</b> Disconfirming evidence</span>
           </div>''',
        unsafe_allow_html=True,
    )


def plotly_base(fig: go.Figure, height: int = 410, y_title: str = "") -> go.Figure:
    font_color = "#4d607a" if LIGHT_MODE else "#aebbd0"
    grid_color = "rgba(54,79,116,.12)" if LIGHT_MODE else "rgba(145,166,202,.10)"
    zero_color = "rgba(54,79,116,.20)" if LIGHT_MODE else "rgba(145,166,202,.18)"
    hover_bg = "rgba(255,255,255,.96)" if LIGHT_MODE else "rgba(18,27,45,.96)"
    hover_font = "#142038" if LIGHT_MODE else "#eef4ff"
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=26, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=font_color, family="Arial, sans-serif", size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=hover_bg, font_color=hover_font, bordercolor=grid_color),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(gridcolor=grid_color, showline=False),
        yaxis=dict(gridcolor=grid_color, title=y_title, zerolinecolor=zero_color),
    )
    return fig


# -----------------------------------------------------------------------------
# Data functions
# -----------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def market_history(
    tickers: tuple[str, ...],
    period: str = "3mo",
    start: str = "",
    end: str = "",
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    try:
        kwargs: dict[str, Any] = {
            "tickers": list(tickers),
            "auto_adjust": True,
            "progress": False,
            "threads": True,
        }
        if start:
            kwargs["start"] = start
            kwargs["end"] = end or None
        else:
            kwargs["period"] = period
        raw = yf.download(**kwargs)
        if raw.empty:
            return pd.DataFrame()

        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw[["Close"]].copy()
            close.columns = [tickers[0]]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])
        close.index = pd.to_datetime(close.index).tz_localize(None)
        return close.dropna(how="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def market_snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    history = market_history(tickers, period="3mo")
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        series = history[ticker].dropna() if not history.empty and ticker in history.columns else pd.Series(dtype=float)
        last = float(series.iloc[-1]) if len(series) else np.nan
        d1 = (last / float(series.iloc[-2]) - 1) * 100 if len(series) >= 2 else np.nan
        d5 = (last / float(series.iloc[-6]) - 1) * 100 if len(series) >= 6 else np.nan
        d21 = (last / float(series.iloc[-22]) - 1) * 100 if len(series) >= 22 else np.nan
        name = MARKETS.get(ticker, {}).get("name") or WATCHLIST.get(ticker, {}).get("name") or ticker
        rows.append({"Ticker": ticker, "Name": name, "Last": last, "1D %": d1, "5D %": d5, "1M %": d21})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def fred_series(series_id: str, api_key: str) -> pd.Series:
    if not api_key:
        return pd.Series(dtype=float)
    try:
        response = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "asc",
                "observation_start": "1945-01-01",
                "limit": 100000,
            },
            timeout=25,
        )
        response.raise_for_status()
        values: dict[pd.Timestamp, float] = {}
        for observation in response.json().get("observations", []):
            raw_value = observation.get("value")
            if raw_value not in (None, "."):
                values[pd.to_datetime(observation["date"])] = float(raw_value)
        return pd.Series(values, dtype=float).sort_index()
    except Exception:
        return pd.Series(dtype=float)


def transform_fred(series: pd.Series, transform: str) -> pd.Series:
    clean = series.dropna().sort_index()
    if transform == "yoy":
        return clean.pct_change(12, fill_method=None).mul(100).dropna()
    if transform == "thousands":
        return clean.div(1000)
    return clean


def value_at_or_before(series: pd.Series, target: pd.Timestamp) -> float | None:
    subset = series.loc[series.index <= target]
    return float(subset.iloc[-1]) if not subset.empty else None


def fred_delta_text(current: float | None, comparison: float | None, mode: str) -> tuple[str, str]:
    if current is None or comparison is None:
        return "—", "neutral"
    difference = current - comparison
    kind = "green" if difference > 0 else "red" if difference < 0 else "neutral"
    if mode == "bp":
        return f"{difference * 100:+.0f} bp", kind
    if mode == "pp":
        return f"{difference:+.2f} pp", kind
    if mode == "percent":
        if comparison == 0:
            return "—", "neutral"
        return f"{(current / comparison - 1) * 100:+.1f}%", kind
    return f"{difference:+.2f}", kind


@st.cache_data(ttl=3600, show_spinner=False)
def boe_rate() -> tuple[str, str]:
    url = "https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate"
    try:
        response = requests.get(url, timeout=18, headers={"User-Agent": "Market Lens educational dashboard"})
        response.raise_for_status()
        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
        match = re.search(r"Current Bank Rate\s*([0-9]+(?:\.[0-9]+)?)\s*%", text, flags=re.I)
        return (f"{match.group(1)}%" if match else "Open source", url)
    except Exception:
        return "Open source", url


@st.cache_data(ttl=3600, show_spinner=False)
def ecb_rate() -> tuple[str, str]:
    url = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"
    try:
        tables = pd.read_html(url)
        for table in tables:
            flat = " ".join(map(str, table.columns))
            if "Deposit facility" in flat:
                numeric = table.apply(pd.to_numeric, errors="coerce").stack().dropna()
                if not numeric.empty:
                    candidates = [float(x) for x in numeric if -1 <= float(x) <= 20]
                    if candidates:
                        return f"{candidates[-1]:.2f}%", url
        return "Open source", url
    except Exception:
        return "Open source", url


@st.cache_data(ttl=900, show_spinner=False)
def google_news(query: str, lookback_days: int, maximum: int) -> pd.DataFrame:
    if not query.strip():
        return pd.DataFrame()
    dated_query = f"{query} when:{lookback_days}d"
    url = f"https://news.google.com/rss/search?q={quote_plus(dated_query)}&hl=en-GB&gl=GB&ceid=GB:en"
    try:
        response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0 MarketLens/2.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        rows: list[dict[str, str]] = []
        for item in soup.find_all("item")[:maximum]:
            source_node = item.find("source")
            rows.append(
                {
                    "Title": item.title.get_text(" ", strip=True) if item.title else "Untitled",
                    "Source": source_node.get_text(" ", strip=True) if source_node else "Unknown",
                    "Published": item.pubDate.get_text(" ", strip=True) if item.pubDate else "",
                    "URL": item.link.get_text(" ", strip=True) if item.link else "",
                }
            )
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def headline_tags(title: str) -> list[str]:
    text = f" {title.lower()} "
    tags: list[str] = []
    rules = {
        "Rates": ["federal reserve", "fed ", "interest rate", "treasury yield", "inflation", "cpi", "pce"],
        "AI CapEx": ["ai ", "artificial intelligence", "data center", "data centre", "gpu", "cloud", "capex"],
        "Memory": ["micron", "hbm", "dram", "memory chip"],
        "Power": ["power grid", "electricity", "natural gas", "fuel cell", "nuclear"],
        "FX": ["dollar", "sterling", "pound", "euro", "yen", "currency"],
        "Policy": ["tariff", "sanction", "export control", "regulation", "trade policy"],
    }
    for tag, words in rules.items():
        if any(word in text for word in words):
            tags.append(tag)
    return tags or ["Markets"]


def portfolio_relevance(title: str) -> tuple[int, list[str]]:
    text = title.lower()
    matched: list[str] = []
    for ticker, profile in WATCHLIST.items():
        if any(keyword in text for keyword in profile["keywords"]):
            matched.append(ticker)
    generic = ["data center", "data centre", "gpu", "hbm", "ai cloud", "power grid", "capex"]
    score = min(5, len(matched) * 2 + sum(1 for keyword in generic if keyword in text))
    return score, matched


def news_why_it_matters(title: str) -> str:
    text = title.lower()
    if any(word in text for word in ["capex", "data center", "data centre", "gpu", "cloud"]):
        return "Check whether this changes AI capacity demand, supplier orders, power requirements or hyperscaler free cash flow."
    if any(word in text for word in ["inflation", "cpi", "pce", "federal reserve", "interest rate"]):
        return "Translate the surprise into the expected policy path, 2Y yield, dollar and discount-rate impact."
    if any(word in text for word in ["tariff", "sanction", "export control"]):
        return "Separate direct revenue exposure from second-order supply-chain, cost and competitive effects."
    if any(word in text for word in ["oil", "natural gas", "electricity", "power"]):
        return "Assess inflation, operating costs, grid constraints and which part of the energy value chain benefits."
    return "Ask what changed versus expectations, which cash-flow channel is affected and what is already priced."


def rebase_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Rebase every column to its own first valid observation."""
    rebased = pd.DataFrame(index=frame.index)
    for column in frame.columns:
        series = frame[column].dropna()
        if not series.empty and float(series.iloc[0]) != 0:
            rebased[column] = frame[column].div(float(series.iloc[0])).mul(100)
    return rebased.dropna(how="all")


def filter_date_range(series: pd.Series, range_choice: str, custom_start: date | None = None, custom_end: date | None = None) -> pd.Series:
    if series.empty:
        return series
    end_ts = pd.Timestamp(custom_end) if custom_end else series.index.max()
    if range_choice == "Max":
        start_ts = series.index.min()
    elif range_choice == "Custom" and custom_start:
        start_ts = pd.Timestamp(custom_start)
    else:
        start_ts = end_ts - pd.Timedelta(days=RANGE_DAYS.get(range_choice, 365 * 5))
    return series.loc[(series.index >= start_ts) & (series.index <= end_ts)]


def cross_asset_brief(snapshot_df: pd.DataFrame) -> tuple[str, str, list[tuple[str, str]]]:
    if snapshot_df.empty:
        return "Data unavailable", "amber", [("Live tape", "Market data could not be loaded. Retry shortly.")]
    data = snapshot_df.set_index("Ticker")

    def get(ticker: str, column: str) -> float | None:
        return safe_float(data.loc[ticker, column]) if ticker in data.index else None

    nasdaq = get("^IXIC", "1D %")
    chips = get("^SOX", "1D %")
    vix = get("^VIX", "Last")
    vix_change = get("^VIX", "1D %")
    dollar = get("DX-Y.NYB", "1D %")
    ten_year = get("^TNX", "1D %")
    oil_5d = get("CL=F", "5D %")

    score = 0
    if nasdaq is not None:
        score += 1 if nasdaq > 0 else -1
    if chips is not None:
        score += 1 if chips > 0 else -1
    if vix_change is not None:
        score += 1 if vix_change < 0 else -1

    if score >= 2:
        regime, kind = "Risk-on bias", "green"
    elif score <= -2:
        regime, kind = "Risk-off bias", "red"
    else:
        regime, kind = "Mixed regime", "amber"

    items: list[tuple[str, str]] = []
    if nasdaq is not None and chips is not None:
        lead = "semiconductors are leading" if chips > nasdaq else "broad tech is leading"
        items.append(("Equity leadership", f"Nasdaq {nasdaq:+.2f}% versus semiconductors {chips:+.2f}%; {lead}."))
    if vix is not None:
        state = "elevated" if vix >= 30 else "above calm conditions" if vix >= 20 else "contained"
        items.append(("Volatility", f"VIX is {vix:.1f}, so implied volatility is {state}."))
    if dollar is not None and ten_year is not None:
        items.append(("Rates and dollar", f"US 10Y changed {ten_year:+.2f}% today while DXY changed {dollar:+.2f}%; watch whether tighter financial conditions pressure duration assets."))
    if oil_5d is not None and abs(oil_5d) >= 2:
        items.append(("Inflation impulse", f"WTI moved {oil_5d:+.1f}% over five sessions, large enough to revisit inflation and consumer-income effects."))
    if not items:
        items.append(("Signal quality", "No unusually large cross-asset move was detected; avoid forcing a narrative."))
    return regime, kind, items[:4]


def fred_interpretation(series_id: str, series: pd.Series) -> str:
    if series.empty:
        return "No interpretation available."
    latest = float(series.iloc[-1])
    three_month = value_at_or_before(series, series.index[-1] - pd.DateOffset(months=3))
    change = latest - three_month if three_month is not None else 0

    if series_id == "UNRATE":
        if change >= 0.3:
            return "失業率近三個月明顯上升。這是增長降溫訊號，但需要與非農、初領失業救濟和工時一起確認。"
        if change <= -0.2:
            return "失業率近三個月下降，勞動市場仍具韌性；這可能降低央行快速寬鬆的必要性。"
        return "失業率近三個月變化有限。單一月份不足以確認轉折，重點看趨勢與其他勞動數據。"
    if series_id in {"CPIAUCSL", "CPILFESL", "PCEPILFE"}:
        if change > 0.2:
            return "同比通脹動能較三個月前回升，市場可能重新評估減息速度與終點利率。"
        if change < -0.2:
            return "同比通脹較三個月前降溫，但交易反應仍取決於 Actual 相對 Consensus。"
        return "同比通脹變化不大。應進一步拆分住房、服務、工資與短期年化趨勢。"
    if series_id in {"DGS2", "DGS10", "DFII10", "DFF"}:
        if change > 0.20:
            return "收益率近三個月上升，金融條件偏緊；高估值和高融資需求資產通常更敏感。"
        if change < -0.20:
            return "收益率近三個月下降，折現率壓力減輕；但需判斷原因是通脹改善還是增長轉弱。"
        return "收益率近三個月相對穩定，短期市場可能更受數據意外與央行措辭驅動。"
    if series_id == "BAMLH0A0HYM2":
        if change > 0.30:
            return "高收益債利差擴大，顯示信用風險與融資壓力正在上升。"
        if change < -0.30:
            return "高收益債利差收窄，風險偏好與融資環境有所改善。"
        return "信用利差暫時穩定；仍要留意低評級企業的再融資需求。"
    return "先判斷方向、變化速度和市場預期，再把數據連到收入、利潤率、資金成本與估值。"


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
try:
    secret_key = str(st.secrets.get("FRED_API_KEY", ""))
except Exception:
    secret_key = ""

st.sidebar.markdown(
    """
    <div class="ml-brand">
      <div class="ml-logo">ML</div>
      <div><div class="ml-brand-title">Market Lens <span class="ml-version">2.3</span></div><div class="ml-brand-sub">Ryan's buy-side research workspace</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.toggle(
    "☀️ 淺色模式 Light mode",
    key="light_mode",
    help="Switch between the dashboard's light and dark themes.",
)

# Browser-side clock: updates every second without rerunning Streamlit or refetching data.
clock_theme = {
    "bg": "#f7f9fc" if LIGHT_MODE else "rgba(15, 23, 39, .82)",
    "border": "rgba(42, 64, 98, .14)" if LIGHT_MODE else "rgba(145, 166, 202, .20)",
    "text": "#17243b" if LIGHT_MODE else "#f4f7fb",
    "muted": "#66768e" if LIGHT_MODE else "#93a2ba",
    "accent": "#1877d2" if LIGHT_MODE else "#56d4dd",
}
components.html(
    f"""
    <div class="clock-card">
      <div class="clock-label">LONDON · LIVE</div>
      <div id="ml-time" class="clock-time">--:--:--</div>
      <div id="ml-date" class="clock-date">Loading date…</div>
      <div id="ml-utc" class="clock-utc">UTC --:--:--</div>
    </div>
    <style>
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; background: transparent; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
      .clock-card {{
        border: 1px solid {clock_theme['border']};
        border-radius: 14px;
        background: {clock_theme['bg']};
        padding: 11px 13px 10px;
        color: {clock_theme['text']};
      }}
      .clock-label {{ color: {clock_theme['accent']}; font-size: 10px; font-weight: 800; letter-spacing: .14em; }}
      .clock-time {{ margin-top: 3px; font-size: 27px; line-height: 1.08; font-weight: 780; letter-spacing: .035em; font-variant-numeric: tabular-nums; }}
      .clock-date {{ margin-top: 4px; color: {clock_theme['muted']}; font-size: 12px; }}
      .clock-utc {{ margin-top: 5px; color: {clock_theme['muted']}; font-size: 10px; font-variant-numeric: tabular-nums; }}
    </style>
    <script>
      const timeEl = document.getElementById('ml-time');
      const dateEl = document.getElementById('ml-date');
      const utcEl = document.getElementById('ml-utc');
      const londonTime = new Intl.DateTimeFormat('en-GB', {{
        timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      }});
      const londonDate = new Intl.DateTimeFormat('zh-Hant-GB', {{
        timeZone: 'Europe/London', weekday: 'short', year: 'numeric', month: 'long', day: 'numeric'
      }});
      const utcTime = new Intl.DateTimeFormat('en-GB', {{
        timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      }});
      function tick() {{
        const now = new Date();
        timeEl.textContent = londonTime.format(now);
        dateEl.textContent = londonDate.format(now);
        utcEl.textContent = 'UTC ' + utcTime.format(now);
      }}
      tick();
      setInterval(tick, 1000);
    </script>
    """,
    height=104,
)

if secret_key:
    st.sidebar.markdown(f"{badge('FRED connected', 'green')}", unsafe_allow_html=True)
    fred_key = secret_key
    with st.sidebar.expander("Data settings"):
        st.caption("FRED key is loaded securely from Streamlit Secrets.")
else:
    st.sidebar.markdown(f"{badge('FRED key needed', 'amber')}", unsafe_allow_html=True)
    with st.sidebar.expander("Data settings", expanded=True):
        fred_key = st.text_input("FRED API key", type="password", help="For a permanent setup, save it in Streamlit Secrets rather than GitHub.")

NAV_ITEMS = [
    "⌂  晨間簡報 Briefing",
    "◫  宏觀實驗室 Macro Lab",
    "⚡  AI基建 AI Infrastructure",
    "◉  新聞雷達 News Radar",
    "◇  投資組合 Portfolio",
    "△  學習實驗室 Learning",
    "✎  研究筆記 Research",
]
page = st.sidebar.radio("Navigate", NAV_ITEMS, label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.caption("Educational research tool, not investment advice. Verify important facts with primary sources.")
st.sidebar.caption("Data: Yahoo Finance · FRED · official central-bank pages · Google News RSS")


# -----------------------------------------------------------------------------
# Page: Morning Briefing
# -----------------------------------------------------------------------------
if page.startswith("⌂"):
    hero(
        "Daily decision dashboard",
        "今天市場真正交易什麼？",
        "先看跨資產價格，再找宏觀驅動、傳導渠道與可能推翻論點的證據。",
        ["Cross-asset", "Rates", "FX", "AI CapEx", "Portfolio impact"],
    )

    snapshot_df = market_snapshot(tuple(MARKETS))
    snapshot_index = snapshot_df.set_index("Ticker") if not snapshot_df.empty else pd.DataFrame()

    section_label("Live market pulse")
    card_tickers = ["^GSPC", "^IXIC", "^SOX", "^VIX", "^TNX", "GBPUSD=X"]
    card_cols = st.columns(6)
    for index, ticker in enumerate(card_tickers):
        with card_cols[index]:
            if not snapshot_index.empty and ticker in snapshot_index.index:
                last = safe_float(snapshot_index.loc[ticker, "Last"])
                one_day = safe_float(snapshot_index.loc[ticker, "1D %"])
                suffix = "%" if ticker == "^TNX" else ""
                stat_card(
                    MARKETS[ticker]["name"],
                    f"{fmt_number(last)}{suffix}",
                    fmt_pct(one_day),
                    "1D move",
                    delta_class(one_day),
                )
            else:
                stat_card(MARKETS[ticker]["name"], "—", "Data unavailable", "", "ml-neu")

    regime, regime_kind, brief_items = cross_asset_brief(snapshot_df)
    section_label("Today in 60 seconds")
    left, right = st.columns([1.65, 1])
    with left:
        for idx, (title, body) in enumerate(brief_items, start=1):
            brief_card(idx, title, body)
    with right:
        st.markdown(
            f"""
            <div class="ml-card" style="min-height:100%">
              <div class="ml-card-title">RULES-BASED REGIME READ</div>
              <div style="margin-top:.75rem">{badge(regime, regime_kind)}</div>
              <div class="ml-card-value" style="font-size:1.28rem;margin-top:1rem">Do not confuse direction with thesis.</div>
              <div class="ml-card-meta" style="margin-top:.7rem">The label combines equity leadership and volatility. It does not know positioning, valuation or expectations.</div>
              <div style="margin-top:1rem;color:#c8d3e2;font-size:.86rem"><b>Next question:</b> Is the move caused by discount rates, cash-flow expectations, liquidity, or all three?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    section_label("Cross-asset tape")
    if snapshot_df.empty:
        st.warning("Live market data could not be loaded. Yahoo Finance may be temporarily unavailable.")
    else:
        display_tape = snapshot_df.copy()
        display_tape["Asset class"] = display_tape["Ticker"].map(lambda x: MARKETS.get(x, {}).get("group", "Other"))
        display_tape = display_tape[["Asset class", "Name", "Ticker", "Last", "1D %", "5D %", "1M %"]]
        st.markdown(market_tape_html(display_tape), unsafe_allow_html=True)
        with st.expander("Open raw data / download view"):
            st.dataframe(
                display_tape.style.format({"Last": "{:,.2f}", "1D %": "{:+.2f}%", "5D %": "{:+.2f}%", "1M %": "{:+.2f}%"}),
                hide_index=True,
                use_container_width=True,
                height=390,
            )

    section_label("Central-bank snapshot")
    fed = fred_series("DFF", fred_key) if fred_key else pd.Series(dtype=float)
    boe_value, boe_url = boe_rate()
    ecb_value, ecb_url = ecb_rate()
    cb_cols = st.columns(3)
    with cb_cols[0]:
        central_bank_card(
            "Federal Reserve",
            f"{fed.iloc[-1]:.2f}%" if not fed.empty else "Add FRED key",
            "Effective fed funds",
            "Policy path matters more than the latest decision",
            "https://www.federalreserve.gov/monetarypolicy.htm",
        )
    with cb_cols[1]:
        central_bank_card("Bank of England", boe_value, "Bank Rate", "Watch services inflation, wages and vote split", boe_url)
    with cb_cols[2]:
        central_bank_card("European Central Bank", ecb_value, "Deposit facility", "Watch wages, energy, euro and fragmentation", ecb_url)

    discipline_strip()


# -----------------------------------------------------------------------------
# Page: Macro Lab
# -----------------------------------------------------------------------------
elif page.startswith("◫"):
    hero(
        "Macro lab",
        "從長期歷史切換到可交易的時間窗口",
        "每個指標都能選擇 1Y、3Y、5Y、10Y、Max 或自訂日期，並比較最新值、前值、三個月和一年前。",
        ["Date controls", "FRED", "Expectation framework", "Interactive charts"],
    )

    market_tab, fred_tab, regime_tab = st.tabs(["Market map 市場地圖", "FRED Lab 官方宏觀", "Regime framework 環境框架"])

    with market_tab:
        controls_a, controls_b = st.columns([2.2, 1])
        with controls_a:
            selected_market = st.multiselect(
                "Market series",
                options=list(MARKETS),
                default=["^GSPC", "^SOX", "^VIX", "^TNX", "DX-Y.NYB", "CL=F"],
                format_func=lambda ticker: f"{MARKETS[ticker]['name']} ({ticker})",
            )
        with controls_b:
            market_range = st.segmented_control("History", list(MARKET_PERIODS), default="1Y", selection_mode="single") or "1Y"

        market_df = market_history(tuple(selected_market), period=MARKET_PERIODS[market_range])
        if market_df.empty:
            st.warning("Market history could not be loaded.")
        else:
            normalized = rebase_frame(market_df.ffill())
            fig = go.Figure()
            for ticker in normalized.columns:
                fig.add_trace(
                    go.Scatter(
                        x=normalized.index,
                        y=normalized[ticker],
                        mode="lines",
                        name=MARKETS.get(ticker, {}).get("name", ticker),
                        line=dict(width=2.3),
                        hovertemplate="%{y:.1f}<extra></extra>",
                    )
                )
            fig = plotly_base(fig, height=460, y_title="Rebased to 100")
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
            st.caption("All selected market series are rebased to 100 so assets with different units can be compared.")

    with fred_tab:
        if not fred_key:
            st.warning("Add the FRED API key in the sidebar or Streamlit Secrets to activate official macro data.")
            st.code('FRED_API_KEY = "your_key_here"', language="toml")
        else:
            control_left, control_right = st.columns([2, 1.15])
            with control_left:
                series_id = st.selectbox(
                    "FRED series",
                    options=list(FRED_SERIES),
                    format_func=lambda key: f"{FRED_SERIES[key]['name']} ({key})",
                )
            with control_right:
                range_choice = st.segmented_control(
                    "Visible range",
                    ["1Y", "3Y", "5Y", "10Y", "Max", "Custom"],
                    default="5Y",
                    selection_mode="single",
                ) or "5Y"

            custom_start: date | None = None
            custom_end: date | None = None
            if range_choice == "Custom":
                date_cols = st.columns(2)
                with date_cols[0]:
                    custom_start = st.date_input("Start date", value=date.today() - timedelta(days=365 * 5), max_value=date.today())
                with date_cols[1]:
                    custom_end = st.date_input("End date", value=date.today(), max_value=date.today())
                if custom_start > custom_end:
                    st.error("Start date must be before the end date.")
                    st.stop()

            meta = FRED_SERIES[series_id]
            raw_series = fred_series(series_id, fred_key)
            transformed = transform_fred(raw_series, meta["transform"])
            visible = filter_date_range(transformed, range_choice, custom_start, custom_end)

            if visible.empty:
                st.error("No FRED observations were returned for this range. Check the API key or widen the dates.")
            else:
                latest_date = transformed.index[-1]
                latest = float(transformed.iloc[-1])
                previous = float(transformed.iloc[-2]) if len(transformed) >= 2 else None
                three_month = value_at_or_before(transformed, latest_date - pd.DateOffset(months=3))
                one_year = value_at_or_before(transformed, latest_date - pd.DateOffset(years=1))

                prev_text, prev_kind = fred_delta_text(latest, previous, meta["change"])
                three_text, three_kind = fred_delta_text(latest, three_month, meta["change"])
                year_text, year_kind = fred_delta_text(latest, one_year, meta["change"])

                metric_cols = st.columns(4)
                with metric_cols[0]:
                    stat_card("Latest", f"{latest:,.2f}", latest_date.strftime("%d %b %Y"), meta["unit"], "ml-neu")
                with metric_cols[1]:
                    stat_card("Versus previous", prev_text, f"Previous: {fmt_number(previous)}", meta["frequency"], {"green": "ml-pos", "red": "ml-neg"}.get(prev_kind, "ml-neu"))
                with metric_cols[2]:
                    stat_card("3-month change", three_text, f"Then: {fmt_number(three_month)}", "Trend check", {"green": "ml-pos", "red": "ml-neg"}.get(three_kind, "ml-neu"))
                with metric_cols[3]:
                    stat_card("1-year change", year_text, f"Then: {fmt_number(one_year)}", "Cycle context", {"green": "ml-pos", "red": "ml-neg"}.get(year_kind, "ml-neu"))

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=visible.index,
                        y=visible.values,
                        mode="lines",
                        name=meta["short"],
                        line=dict(width=3, color="#68b7ff"),
                        fill="tozeroy" if series_id in {"BAMLH0A0HYM2", "ICSA"} else None,
                        fillcolor="rgba(104,183,255,.08)",
                        hovertemplate=f"%{{x|%d %b %Y}}<br>%{{y:.2f}} {meta['unit']}<extra></extra>",
                    )
                )
                fig.add_hline(y=latest, line_dash="dot", line_color="rgba(86,212,221,.55)", annotation_text=f"Latest {latest:.2f}")
                fig = plotly_base(fig, height=470, y_title=meta["unit"])
                fig.update_xaxes(rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

                st.markdown(
                    f"""
                    <div class="ml-card">
                      <div class="ml-card-title">HOW TO READ THIS</div>
                      <div style="font-size:1.02rem;margin-top:.55rem;color:#d7dfeb">{esc(fred_interpretation(series_id, transformed))}</div>
                      <div class="ml-card-meta" style="margin-top:.65rem">Do not infer the market reaction from the data level alone. Compare actual versus consensus and observe rates, dollar, credit and equities together.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with regime_tab:
        regime_df = pd.DataFrame(
            [
                ["Inflation", "CPI, core PCE, wages, oil", "Faster or slower than priced?", "2Y yield, dollar, growth valuation"],
                ["Growth", "PMI, payrolls, claims, retail sales", "Resilient, reaccelerating or contracting?", "Cyclicals, credit, earnings revisions"],
                ["Policy", "2Y yield, futures, speeches", "What path is already priced?", "Curve, FX, duration assets"],
                ["Liquidity", "Dollar, credit spreads, bank standards", "Easing or tightening?", "High-debt and high-CapEx companies"],
                ["Risk appetite", "VIX, breadth, credit, small caps", "Is the move broad and fundamental?", "Position sizing and hedging"],
            ],
            columns=["Pillar", "Indicators", "Core question", "Transmission"],
        )
        st.dataframe(regime_df, hide_index=True, use_container_width=True, height=300)
        st.info("A regime is not a forecast. It is a compact description of the current combination of inflation, growth, policy, liquidity and risk appetite.")


# -----------------------------------------------------------------------------
# Page: AI Infrastructure
# -----------------------------------------------------------------------------
elif page.startswith("⚡"):
    hero(
        "AI infrastructure stack",
        "把持倉放回整條產業鏈",
        "Hyperscaler CapEx → AI Cloud → Data Centre → GPU / HBM → Power。不要只問股價升跌，要問需求從哪一層傳到哪一層。",
        ["GOOGL / MSFT", "NBIS", "APLD", "MU", "BE / TE"],
    )

    section_label("Value chain")
    chain_cols = st.columns(5)
    chain = [
        ("01", "Hyperscalers", "CapEx budget and demand signal"),
        ("02", "AI Cloud", "GPU capacity and utilisation"),
        ("03", "Data centres", "Lease, construction and power"),
        ("04", "Compute & memory", "GPU, HBM and networking"),
        ("05", "Power", "Grid, on-site supply and fuel"),
    ]
    for col, (number, name, text) in zip(chain_cols, chain):
        with col:
            st.markdown(
                f'<div class="ml-card"><div class="ml-eyebrow" style="margin:0">{number}</div><div class="ml-card-value" style="font-size:1.15rem">{esc(name)}</div><div class="ml-card-meta">{esc(text)}</div></div>',
                unsafe_allow_html=True,
            )

    infra_tickers = tuple(WATCHLIST)
    infra_snapshot = market_snapshot(infra_tickers)
    section_label("Live watchlist")
    if infra_snapshot.empty:
        st.warning("Live watchlist data is currently unavailable.")
    else:
        infra_display = infra_snapshot.copy()
        infra_display["Layer"] = infra_display["Ticker"].map(lambda ticker: WATCHLIST[ticker]["layer"])
        infra_display = infra_display[["Ticker", "Name", "Layer", "Last", "1D %", "5D %", "1M %"]]
        st.dataframe(
            infra_display.style.format({"Last": "{:,.2f}", "1D %": "{:+.2f}%", "5D %": "{:+.2f}%", "1M %": "{:+.2f}%"}),
            hide_index=True,
            use_container_width=True,
            height=330,
        )

    performance_controls = st.columns([2.2, 1])
    with performance_controls[0]:
        compare_tickers = st.multiselect("Compare companies", list(WATCHLIST), default=["APLD", "MU", "NBIS", "BE"], format_func=lambda x: f"{x} · {WATCHLIST[x]['name']}")
    with performance_controls[1]:
        compare_range = st.segmented_control("History", ["1M", "3M", "6M", "1Y", "3Y"], default="6M", selection_mode="single") or "6M"

    comparison = market_history(tuple(compare_tickers), period=MARKET_PERIODS[compare_range])
    if not comparison.empty:
        normalized = rebase_frame(comparison.ffill())
        fig = go.Figure()
        for ticker in normalized.columns:
            fig.add_trace(go.Scatter(x=normalized.index, y=normalized[ticker], mode="lines", name=ticker, line=dict(width=2.4), hovertemplate="%{y:.1f}<extra></extra>"))
        fig = plotly_base(fig, height=430, y_title="Rebased to 100")
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

    section_label("Company thesis map")
    selected_company = st.selectbox("Select a company", list(WATCHLIST), format_func=lambda ticker: f"{ticker} · {WATCHLIST[ticker]['name']}")
    profile = WATCHLIST[selected_company]
    thesis_cols = st.columns(3)
    with thesis_cols[0]:
        st.markdown(f'<div class="ml-card"><div class="ml-card-title">PRIMARY DRIVER</div><div style="margin-top:.65rem">{esc(profile["driver"])}</div></div>', unsafe_allow_html=True)
    with thesis_cols[1]:
        st.markdown(f'<div class="ml-card"><div class="ml-card-title">BULL CASE</div><div style="margin-top:.65rem">{esc(profile["bull"])}</div></div>', unsafe_allow_html=True)
    with thesis_cols[2]:
        st.markdown(f'<div class="ml-card"><div class="ml-card-title">DISCONFIRMING SIGNAL</div><div style="margin-top:.65rem">{esc(profile["disconfirm"])}</div></div>', unsafe_allow_html=True)

    section_label("Shock transmission")
    selected_shock = st.selectbox("Scenario", list(SHOCKS))
    shock_cols = st.columns(len(SHOCKS[selected_shock]))
    for col, (asset, direction, confidence) in zip(shock_cols, SHOCKS[selected_shock]):
        with col:
            st.markdown(
                f'<div class="ml-card"><div class="ml-card-title">{esc(asset)}</div><div style="font-weight:700;margin-top:.55rem">{esc(direction)}</div><div class="ml-card-meta">Confidence: {esc(confidence)}</div></div>',
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# Page: News Radar
# -----------------------------------------------------------------------------
elif page.startswith("◉"):
    hero(
        "News radar",
        "新聞不是資訊流，而是變化偵測器",
        "聚合標題與原文連結，但不抓取付費文章全文。每條新聞都先標記主題、持倉關聯與傳導問題。",
        ["Google News RSS", "WSJ-friendly links", "Primary sources", "Portfolio relevance"],
    )

    news_controls = st.columns([1.5, 2.2, .8, .8])
    with news_controls[0]:
        news_theme = st.selectbox("Theme", list(NEWS_PRESETS))
    with news_controls[1]:
        news_query = st.text_input("Search query", NEWS_PRESETS[news_theme])
    with news_controls[2]:
        lookback = st.selectbox("Lookback", [1, 3, 7, 14], index=1, format_func=lambda x: f"{x} day" if x == 1 else f"{x} days")
    with news_controls[3]:
        maximum = st.selectbox("Articles", [10, 20, 30, 50], index=1)

    portfolio_only = st.toggle("Prioritise headlines related to the AI infrastructure watchlist", value=True)
    news_df = google_news(news_query, lookback, maximum)

    if news_df.empty:
        st.warning("No live articles were returned. Google News RSS may be temporarily unavailable; use the primary-source links below.")
    else:
        scores = news_df["Title"].apply(portfolio_relevance)
        news_df["Relevance"] = scores.apply(lambda x: x[0])
        news_df["Matched"] = scores.apply(lambda x: ", ".join(x[1]))
        if portfolio_only:
            news_df = news_df.sort_values(["Relevance", "Published"], ascending=[False, False])

        for row_number, (_, row) in enumerate(news_df.iterrows()):
            tags = headline_tags(row["Title"])
            score = int(row["Relevance"])
            kind = "green" if score >= 3 else "amber" if score >= 1 else "neutral"
            matched = f" · Matched: {row['Matched']}" if row["Matched"] else ""
            tag_html = " ".join(badge(tag, "neutral") for tag in tags)
            st.markdown(
                f"""
                <div class="ml-card" style="margin:.65rem 0">
                  <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap">
                    <div style="font-size:1.05rem;font-weight:720;max-width:980px">{esc(row['Title'])}</div>
                    <div>{badge(f'Relevance {score}/5', kind)}</div>
                  </div>
                  <div class="ml-card-meta" style="margin-top:.38rem">{esc(row['Source'])} · {esc(row['Published'])}{esc(matched)}</div>
                  <div style="margin-top:.7rem">{tag_html}</div>
                  <div style="margin-top:.75rem;color:#c5d0df;font-size:.88rem"><b>Why it matters:</b> {esc(news_why_it_matters(row['Title']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if row["URL"]:
                st.link_button("Open original article", row["URL"])

        st.download_button("Download headline list", news_df.to_csv(index=False).encode("utf-8"), "market_lens_news.csv", "text/csv")

    section_label("Primary-source desk")
    link_cols = st.columns(5)
    primary_links = [
        ("Federal Reserve", "https://www.federalreserve.gov/newsevents.htm"),
        ("Bank of England", "https://www.bankofengland.co.uk/news"),
        ("ECB", "https://www.ecb.europa.eu/press/html/index.en.html"),
        ("SEC filings", "https://www.sec.gov/edgar/search/"),
        ("WSJ", "https://www.wsj.com/"),
    ]
    for col, (label, url) in zip(link_cols, primary_links):
        with col:
            st.link_button(label, url, use_container_width=True)

    st.info("A headline is not a trade. Ask: **What changed versus expectations? Is the source primary? Which cash-flow or discount-rate channel is affected? Is the effect temporary or structural?**")


# -----------------------------------------------------------------------------
# Page: Portfolio
# -----------------------------------------------------------------------------
elif page.startswith("◇"):
    hero(
        "Portfolio cockpit",
        "把價格、持倉與論點放在同一個畫面",
        "資料只保存在目前 Streamlit session；可下載 CSV 備份，下次再上傳。不要在 App 中儲存券商密碼。",
        ["Live prices", "P&L", "Concentration", "Thesis confidence"],
    )

    uploaded_positions = st.file_uploader("Upload a previous position CSV", type=["csv"])
    if uploaded_positions is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_positions)
            required = {"Ticker", "Shares", "Average cost", "Currency", "Thesis confidence (1-5)"}
            if required.issubset(uploaded_df.columns):
                st.session_state["positions_v2"] = uploaded_df
                st.success("Position file loaded.")
            else:
                st.error("The CSV does not contain the expected position columns.")
        except Exception as exc:
            st.error(f"Could not read the CSV: {exc}")

    if "positions_v2" not in st.session_state:
        st.session_state["positions_v2"] = pd.DataFrame(
            [
                {"Ticker": ticker, "Shares": 0.0, "Average cost": 0.0, "Currency": "USD", "Thesis confidence (1-5)": 3, "Notes": ""}
                for ticker in WATCHLIST
            ]
        )

    edited_positions = st.data_editor(
        st.session_state["positions_v2"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.TextColumn(required=True),
            "Shares": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.4f"),
            "Average cost": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.2f"),
            "Currency": st.column_config.SelectboxColumn(options=["USD", "GBP", "EUR", "HKD"]),
            "Thesis confidence (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
            "Notes": st.column_config.TextColumn(width="large"),
        },
        key="position_editor_v2",
    )
    st.session_state["positions_v2"] = edited_positions

    clean_positions = edited_positions.copy()
    clean_positions["Ticker"] = clean_positions["Ticker"].astype(str).str.strip().str.upper()
    clean_positions["Shares"] = pd.to_numeric(clean_positions["Shares"], errors="coerce").fillna(0)
    clean_positions["Average cost"] = pd.to_numeric(clean_positions["Average cost"], errors="coerce").fillna(0)
    active = clean_positions[clean_positions["Shares"] > 0].copy()

    if active.empty:
        st.info("Enter at least one position above to calculate market value and unrealised P&L.")
    else:
        prices = market_snapshot(tuple(active["Ticker"].unique()))[["Ticker", "Last", "1D %"]]
        portfolio = active.merge(prices, on="Ticker", how="left")
        portfolio["Market value"] = portfolio["Shares"] * portfolio["Last"]
        portfolio["Cost basis"] = portfolio["Shares"] * portfolio["Average cost"]
        portfolio["Unrealised P&L"] = portfolio["Market value"] - portfolio["Cost basis"]
        portfolio["P&L %"] = np.where(portfolio["Cost basis"] > 0, portfolio["Unrealised P&L"] / portfolio["Cost basis"] * 100, np.nan)
        total_value = float(portfolio["Market value"].sum(skipna=True))
        total_cost = float(portfolio["Cost basis"].sum(skipna=True))
        total_pnl = total_value - total_cost
        total_pnl_pct = total_pnl / total_cost * 100 if total_cost else np.nan

        summary_cols = st.columns(3)
        with summary_cols[0]:
            stat_card("Market value", f"${total_value:,.2f}", "USD approximation", "No FX conversion", "ml-neu")
        with summary_cols[1]:
            stat_card("Unrealised P&L", f"${total_pnl:,.2f}", fmt_pct(total_pnl_pct), "Before fees and tax", delta_class(total_pnl))
        with summary_cols[2]:
            largest = portfolio.loc[portfolio["Market value"].idxmax(), "Ticker"] if portfolio["Market value"].notna().any() else "—"
            largest_weight = portfolio["Market value"].max() / total_value * 100 if total_value else np.nan
            stat_card("Largest position", str(largest), fmt_pct(largest_weight, signed=False), "Concentration check", "ml-neu")

        show_columns = ["Ticker", "Shares", "Average cost", "Last", "1D %", "Market value", "Unrealised P&L", "P&L %", "Thesis confidence (1-5)"]
        st.dataframe(
            portfolio[show_columns].style.format(
                {
                    "Shares": "{:,.4f}",
                    "Average cost": "${:,.2f}",
                    "Last": "${:,.2f}",
                    "1D %": "{:+.2f}%",
                    "Market value": "${:,.2f}",
                    "Unrealised P&L": "${:,.2f}",
                    "P&L %": "{:+.2f}%",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

        weights = portfolio.dropna(subset=["Market value"]).copy()
        if not weights.empty and weights["Market value"].sum() > 0:
            weights["Weight"] = weights["Market value"] / weights["Market value"].sum() * 100
            fig = go.Figure(go.Bar(x=weights["Ticker"], y=weights["Weight"], text=weights["Weight"].map(lambda x: f"{x:.1f}%"), textposition="outside"))
            fig = plotly_base(fig, height=360, y_title="Portfolio weight %")
            fig.update_traces(marker_color="#68b7ff")
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    st.download_button(
        "Download position log",
        edited_positions.to_csv(index=False).encode("utf-8"),
        "market_lens_positions.csv",
        "text/csv",
        type="primary",
    )


# -----------------------------------------------------------------------------
# Page: Learning
# -----------------------------------------------------------------------------
elif page.startswith("△"):
    hero(
        "Learning lab",
        "每天學一個能改變投資判斷的概念",
        "不是背定義，而是建立：數據 → 預期 → 市場價格 → 企業現金流 → 持倉決策的傳導鏈。",
        ["Daily lesson", "Shock map", "Quiz", "Buy-side habits"],
    )

    topic_names = list(TOPICS)
    daily_topic = topic_names[date.today().toordinal() % len(topic_names)]
    lesson_tab, shock_tab, quiz_tab = st.tabs(["Daily lesson 今日概念", "Shock map 衝擊傳導", "Mini quiz 小測驗"])

    with lesson_tab:
        chosen_topic = st.selectbox("Concept", topic_names, index=topic_names.index(daily_topic))
        definition, watch, transmission, mistake = TOPICS[chosen_topic]
        st.markdown(f"### {chosen_topic}")
        st.write(definition)
        lesson_cols = st.columns(3)
        with lesson_cols[0]:
            st.markdown(f'<div class="ml-card"><div class="ml-card-title">WHAT TO WATCH</div><div style="margin-top:.65rem">{esc(watch)}</div></div>', unsafe_allow_html=True)
        with lesson_cols[1]:
            st.markdown(f'<div class="ml-card"><div class="ml-card-title">TRANSMISSION</div><div style="margin-top:.65rem">{esc(transmission)}</div></div>', unsafe_allow_html=True)
        with lesson_cols[2]:
            st.markdown(f'<div class="ml-card"><div class="ml-card-title">COMMON MISTAKE</div><div style="margin-top:.65rem">{esc(mistake)}</div></div>', unsafe_allow_html=True)
        st.info("**Exercise:** 找一份第一手數據或公司文件，記錄 Consensus、Actual、第一分鐘市場反應、收市反應，以及24小時後是否持續。")

    with shock_tab:
        learning_shock = st.selectbox("Shock", list(SHOCKS), key="learning_shock")
        for number, (asset, direction, confidence) in enumerate(SHOCKS[learning_shock], start=1):
            brief_card(number, asset, f"{direction} · Confidence: {confidence}")
        st.write("**Second-order question:** 這個衝擊只是改變折現率，還是同時影響收入、利潤率、融資能力與競爭格局？")

    with quiz_tab:
        questions = [
            ("CPI低於上月但高於市場預期，短期市場通常最重視甚麼？", ["只看按月方向", "相對市場預期的差異", "指數絕對水平"], "相對市場預期的差異", "市場交易的是新資訊相對已定價預期。"),
            ("10年期實質利率上升為何常壓制高增長股？", ["提高近期銷售", "提高遠期現金流折現率", "自動造成衰退"], "提高遠期現金流折現率", "遠期現金流的現值會下降。"),
            ("EPS超預期但FCF因CapEx急升而轉差，應優先調查甚麼？", ["只看EPS", "CapEx回報與融資是否可信", "自動賣出"], "CapEx回報與融資是否可信", "CapEx可以創造價值，但回報需要高於資金成本。"),
        ]
        correct_count = 0
        answered_count = 0
        for idx, (question, options, answer, explanation) in enumerate(questions):
            choice = st.radio(question, options, key=f"quiz_v2_{idx}", index=None)
            if choice is not None:
                answered_count += 1
                if choice == answer:
                    correct_count += 1
                    st.success("正確。" + explanation)
                else:
                    st.error("不完全正確。" + explanation)
        st.progress(correct_count / len(questions), text=f"Score: {correct_count}/{len(questions)} · Answered {answered_count}/{len(questions)}")


# -----------------------------------------------------------------------------
# Page: Research
# -----------------------------------------------------------------------------
else:
    hero(
        "Research notebook",
        "寫下一個可以被推翻的投資論點",
        "好的研究不是堆砌利好，而是清楚寫出機制、已定價內容、催化因素、反證與倉位規則。",
        ["Thesis", "Disconfirming evidence", "Review date", "Primary sources"],
    )

    builder_tab, notebook_tab = st.tabs(["Thesis builder 論點建立", "Notebook 研究紀錄"])

    with builder_tab:
        asset = st.text_input("Asset or theme", placeholder="e.g. MU / HBM memory cycle")
        why_wrong = st.text_area("Why may the market be wrong?", placeholder="State the disagreement with consensus in one or two sentences.")
        mechanism = st.text_area("Mechanism from event to cash flow", placeholder="Demand → pricing → margin → free cash flow → valuation")
        priced = st.text_area("What may already be priced?", placeholder="Valuation, positioning, consensus growth, expected catalysts")
        catalysts = st.text_area("Three catalysts", placeholder="1.\n2.\n3.")
        disconfirming = st.text_area("Three disconfirming signals", placeholder="1.\n2.\n3.")
        rule = st.text_area("Valuation / position-size rule", placeholder="What price, evidence or risk limit changes the position?")

        if st.button("Generate challenge questions", type="primary"):
            if not any([asset, why_wrong, mechanism, priced, catalysts, disconfirming, rule]):
                st.warning("Enter at least part of the thesis first.")
            else:
                challenge_questions = [
                    "Which assumption contributes most to the valuation, and what observable data would falsify it?",
                    "Could the same bullish evidence already be embedded in consensus estimates or the share price?",
                    "What financing, dilution, customer-concentration or execution risk is missing from the mechanism?",
                    "Which competitor or substitute could capture the economics even if the industry thesis is correct?",
                    "What would make you reduce the position before the headline thesis is fully disproved?",
                ]
                section_label("Challenge the thesis")
                for idx, question in enumerate(challenge_questions, start=1):
                    brief_card(idx, f"Challenge {idx}", question)

        thesis_text = f"""Asset/theme: {asset}
Why the market may be wrong: {why_wrong}
Mechanism from event to cash flow: {mechanism}
What may already be priced: {priced}
Catalysts: {catalysts}
Disconfirming signals: {disconfirming}
Valuation / position-size rule: {rule}
Created: {datetime.now().strftime('%Y-%m-%d')}
"""
        st.download_button("Download thesis as TXT", thesis_text.encode("utf-8"), "market_lens_thesis.txt", "text/plain")

    with notebook_tab:
        if "research_notes_v2" not in st.session_state:
            st.session_state["research_notes_v2"] = pd.DataFrame(
                columns=["Asset / theme", "Core thesis", "Catalyst", "Disconfirming evidence", "Key metric", "Review date", "Confidence (1-5)"]
            )
        notes = st.data_editor(
            st.session_state["research_notes_v2"],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Review date": st.column_config.DateColumn(),
                "Confidence (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
            },
            key="research_editor_v2",
        )
        st.session_state["research_notes_v2"] = notes
        st.download_button("Download research notebook", notes.to_csv(index=False).encode("utf-8"), "market_lens_research_notebook.csv", "text/csv", type="primary")


st.markdown(
    f'<div class="ml-footer">Market Lens 2.3 · Refreshed {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} · Educational use only.</div>',
    unsafe_allow_html=True,
)
