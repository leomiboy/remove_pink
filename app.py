import streamlit as st
import fitz  # PyMuPDF 套件
import cv2
import numpy as np
from PIL import Image
import io

# --- 網頁設定 ---
st.set_page_config(page_title="PDF 粉色浮水印移除", layout="wide")
st.title("📄 試題本粉色浮水印移除工具")

# --- 影像處理核心函數 ---
def process_image(pix, h_min, h_max, s_min, v_min):
    """將 PDF 頁面轉換為圖片，並去除粉紅色"""
    # 1. 轉成 NumPy 陣列
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4: # 處理透明通道
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
    # 2. 轉 HSV 並建立遮罩
    hsv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    lower_pink = np.array([h_min, s_min, v_min])
    upper_pink = np.array([h_max, 255, 255])
    mask = cv2.inRange(hsv_img, lower_pink, upper_pink)
    
    # 3. 替換顏色為純白色
    result_img = img_array.copy()
    result_img[mask > 0] =[255, 255, 255]
    
    return img_array, result_img

# --- 側邊欄：參數微調 ---
st.sidebar.header("🎨 微調粉紅色範圍 (HSV)")
st.sidebar.write("已載入最佳預設值。調整拉桿可即時預覽第一頁效果：")

# 💡 已經將你的最佳參數設為預設值 (最後一個數字)
h_min = st.sidebar.slider("Hue (色相) 最小值", 0, 179, 135)
h_max = st.sidebar.slider("Hue (色相) 最大值", 0, 179, 179)
s_min = st.sidebar.slider("Saturation (飽和度) 最小值", 0, 255, 0)
v_min = st.sidebar.slider("Value (明度) 最小值", 0, 255, 200)

# --- 初始化 Session State ---
# 用來暫存處理完的 PDF 檔案，避免網頁重整後消失
if 'final_pdf_bytes' not in st.session_state:
    st.session_state.final_pdf_bytes = None

# --- 主畫面：上傳區 ---
uploaded_file = st.file_uploader("上傳 PDF 檔案", type=["pdf"])

if uploaded_file is not None:
    # 讀取 PDF
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = doc.page_count
    
    st.write(f"📂 檔案已上傳，共 **{total_pages}** 頁。")
    
    # --- 預覽第一頁 ---
    st.markdown("### 👁️ 第一頁即時預覽")
    page_0 = doc.load_page(0)
    matrix = fitz.Matrix(2.0, 2.0) # 放大2倍保持解析度
    pix_0 = page_0.get_pixmap(matrix=matrix)
    
    # 呼叫處理函數
    orig_img, clean_img = process_image(pix_0, h_min, h_max, s_min, v_min)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("🔍 **原始圖片**")
        st.image(orig_img, use_container_width=True)
    with col2:
        st.write("✨ **處理後 (去除粉色)**")
        st.image(clean_img, use_container_width=True)

    # --- 全部處理與下載區 ---
    st.markdown("---")
    st.markdown("### 🚀 執行全檔處理")
    
    # 當按下按鈕時，開始跑迴圈
    if st.button("開始處理全份文件 (可能需要幾十秒，請稍候)"):
        st.session_state.final_pdf_bytes = None # 每次點擊先清空舊紀錄
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_pil_images =[]
        
        # 逐頁處理迴圈
        for i in range(total_pages):
            status_text.text(f"正在處理第 {i+1} / {total_pages} 頁...")
            
            # 讀取單頁並轉成 pixmap
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix)
            
            # 進行除色處理 (只取回傳的 clean_img_array)
            _, clean_img_array = process_image(pix, h_min, h_max, s_min, v_min)
            
            # 將 OpenCV 陣列 (NumPy) 轉換為 PIL Image 物件，準備打包 PDF
            pil_img = Image.fromarray(clean_img_array)
            processed_pil_images.append(pil_img)
            
            # 更新進度條
            progress_bar.progress((i + 1) / total_pages)
            
        status_text.text("圖片處理完畢！正在打包成 PDF...")
        
        # --- 將所有 PIL 圖片打包成單一 PDF ---
        pdf_buffer = io.BytesIO()
        # 儲存第一張圖，並把後面的圖 append 進去
        processed_pil_images[0].save(
            pdf_buffer, 
            format="PDF", 
            save_all=True, 
            append_images=processed_pil_images[1:], 
            resolution=100.0  # 控制輸出 PDF 的解析度標籤
        )
        
        # 將最終的二進位檔案存入 Session State
        st.session_state.final_pdf_bytes = pdf_buffer.getvalue()
        
        progress_bar.empty()
        status_text.success("🎉 全份文件處理完成！請點擊下方按鈕下載。")

# --- 獨立顯示下載按鈕 ---
# 只要 Session State 裡有產出的 PDF，就在最下方顯示下載按鈕
if st.session_state.final_pdf_bytes is not None:
    st.download_button(
        label="📥 點我下載乾淨版 PDF",
        data=st.session_state.final_pdf_bytes,
        file_name="cleaned_document.pdf",
        mime="application/pdf"
    )