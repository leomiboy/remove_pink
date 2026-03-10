import streamlit as st
import fitz  # PyMuPDF 套件
import cv2
import numpy as np
from PIL import Image

# --- 網頁設定 ---
st.set_page_config(page_title="PDF 粉色浮水印移除", layout="wide")
st.title("📄 試題本粉色浮水印移除工具 (測試版)")

# --- 側邊欄：參數微調 ---
st.sidebar.header("🎨 微調粉紅色範圍 (HSV)")
st.sidebar.write("如果浮水印沒有清乾淨，或黑字被吃掉，請微調這裡：")
# 粉紅色的 Hue (色相) 在 OpenCV 中大約落在 140 ~ 170 之間
h_min = st.sidebar.slider("Hue (色相) 最小值", 0, 179, 135)
h_max = st.sidebar.slider("Hue (色相) 最大值", 0, 179, 179)
s_min = st.sidebar.slider("Saturation (飽和度) 最小值", 0, 255, 15)
v_min = st.sidebar.slider("Value (明度) 最小值", 0, 255, 100)

# --- 主畫面：上傳區 ---
uploaded_file = st.file_uploader("上傳 PDF 檔案來測試 (目前只會預覽第一頁)", type=["pdf"])

if uploaded_file is not None:
    # 1. 使用 PyMuPDF 讀取 PDF
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    page = doc.load_page(0) # 載入第一頁 (index 0)
    
    # 2. 提高解析度轉成圖片 (放大 2 倍，讓字體不模糊)
    matrix = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=matrix)
    
    # 3. 將圖片轉換為 NumPy 陣列 (OpenCV 格式)
    # PyMuPDF 預設抓出來是 RGB 或 RGBA
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4: # 如果有透明通道，轉回純 RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
    # 4. 核心魔法：將 RGB 轉換為 HSV 色彩空間
    hsv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # 定義粉紅色的上下限範圍
    lower_pink = np.array([h_min, s_min, v_min])
    upper_pink = np.array([h_max, 255, 255])
    
    # 5. 建立遮罩 (Mask)：抓出落在粉紅色範圍內的像素
    mask = cv2.inRange(hsv_img, lower_pink, upper_pink)
    
    # 6. 顏色替換：將遮罩範圍內的像素，變成純白色 [255, 255, 255]
    result_img = img_array.copy()
    result_img[mask > 0] =[255, 255, 255]
    
    # --- 顯示對比圖 ---
    st.markdown("### 👁️ 第一頁處理預覽")
    col1, col2 = st.columns(2)
    with col1:
        st.write("🔍 **原始圖片**")
        st.image(img_array, use_container_width=True)
    with col2:
        st.write("✨ **處理後 (去除粉色)**")
        st.image(result_img, use_container_width=True)
        
    st.success("調整左側滑桿，確認粉紅色完美消失且黑字清晰後，我們就可以進行下一步！")