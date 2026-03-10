import streamlit as st
import fitz  # PyMuPDF 套件
import cv2
import numpy as np
from PIL import Image
import io

# --- 網頁設定 ---
st.set_page_config(page_title="PDF 浮水印與解答移除工具", layout="wide")
st.title("📄 試題本浮水印/解答移除工具 (雙色版)")

# --- 影像處理核心函數 ---
def process_image(pix, 
                  remove_pink, p_h_min, p_h_max, p_s_min, p_v_min,
                  remove_blue, b_h_min, b_h_max, b_s_min, b_v_min):
    """將 PDF 頁面轉換為圖片，並依需求去除粉色與藍色"""
    # 1. 轉成 NumPy 陣列
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4: # 處理透明通道
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
    # 2. 轉 HSV
    hsv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    # 3. 建立一個全黑的基礎遮罩
    combined_mask = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
    
    # 4. 如果啟用粉紅色去除，則把粉色遮罩疊加進去
    if remove_pink:
        lower_pink = np.array([p_h_min, p_s_min, p_v_min])
        upper_pink = np.array([p_h_max, 255, 255])
        mask_pink = cv2.inRange(hsv_img, lower_pink, upper_pink)
        combined_mask = cv2.bitwise_or(combined_mask, mask_pink)
        
    # 5. 如果啟用藍色去除，則把藍色遮罩疊加進去
    if remove_blue:
        lower_blue = np.array([b_h_min, b_s_min, b_v_min])
        upper_blue = np.array([b_h_max, 255, 255])
        mask_blue = cv2.inRange(hsv_img, lower_blue, upper_blue)
        combined_mask = cv2.bitwise_or(combined_mask, mask_blue)
    
    # 6. 將遮罩範圍內的像素替換為純白色
    result_img = img_array.copy()
    result_img[combined_mask > 0] =[255, 255, 255]
    
    return img_array, result_img

# --- 側邊欄：參數微調 ---
st.sidebar.header("🎨 浮水印顏色清除設定")
st.sidebar.write("已載入最佳雙色預設值，可直接處理！")

# 【粉色設定區塊】
st.sidebar.markdown("### 🌸 粉色/紅色清除")
remove_pink = st.sidebar.checkbox("啟用去除粉紅色", value=True)
p_h_min = st.sidebar.slider("粉色 Hue 最小值", 0, 179, 135)
p_h_max = st.sidebar.slider("粉色 Hue 最大值", 0, 179, 179)
p_s_min = st.sidebar.slider("粉色 Saturation 最小值", 0, 255, 0)
p_v_min = st.sidebar.slider("粉色 Value 最小值", 0, 255, 200)

st.sidebar.markdown("---")

# 【藍色設定區塊】
st.sidebar.markdown("### 🌊 藍色清除")
remove_blue = st.sidebar.checkbox("啟用去除藍色", value=True)
# 💡 這裡已經替換成你測試出來的最強數據！
b_h_min = st.sidebar.slider("藍色 Hue 最小值", 0, 179, 90)
b_h_max = st.sidebar.slider("藍色 Hue 最大值", 0, 179, 179)
b_s_min = st.sidebar.slider("藍色 Saturation 最小值", 0, 255, 0)
b_v_min = st.sidebar.slider("藍色 Value 最小值", 0, 255, 200)


# --- 初始化 Session State ---
if 'final_pdf_bytes' not in st.session_state:
    st.session_state.final_pdf_bytes = None

# --- 主畫面：上傳區 ---
uploaded_file = st.file_uploader("上傳 PDF 檔案", type=["pdf"])

if uploaded_file is not None:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = doc.page_count
    
    st.write(f"📂 檔案已上傳，共 **{total_pages}** 頁。")
    
    # --- 預覽第一頁 ---
    st.markdown("### 👁️ 第一頁即時預覽")
    page_0 = doc.load_page(0)
    matrix = fitz.Matrix(2.0, 2.0) # 放大2倍保持解析度
    pix_0 = page_0.get_pixmap(matrix=matrix)
    
    # 呼叫處理函數 (帶入粉色與藍色的參數)
    orig_img, clean_img = process_image(
        pix_0, 
        remove_pink, p_h_min, p_h_max, p_s_min, p_v_min,
        remove_blue, b_h_min, b_h_max, b_s_min, b_v_min
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("🔍 **原始圖片**")
        st.image(orig_img, use_container_width=True)
    with col2:
        st.write("✨ **處理後**")
        st.image(clean_img, use_container_width=True)

    # --- 全部處理與下載區 ---
    st.markdown("---")
    st.markdown("### 🚀 執行全檔處理")
    
    if st.button("開始處理全份文件 (可能需要幾十秒，請稍候)"):
        st.session_state.final_pdf_bytes = None 
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_pil_images =[]
        
        for i in range(total_pages):
            status_text.text(f"正在處理第 {i+1} / {total_pages} 頁...")
            
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix)
            
            _, clean_img_array = process_image(
                pix, 
                remove_pink, p_h_min, p_h_max, p_s_min, p_v_min,
                remove_blue, b_h_min, b_h_max, b_s_min, b_v_min
            )
            
            pil_img = Image.fromarray(clean_img_array)
            processed_pil_images.append(pil_img)
            
            progress_bar.progress((i + 1) / total_pages)
            
        status_text.text("圖片處理完畢！正在打包成 PDF...")
        
        pdf_buffer = io.BytesIO()
        processed_pil_images[0].save(
            pdf_buffer, 
            format="PDF", 
            save_all=True, 
            append_images=processed_pil_images[1:], 
            resolution=100.0 
        )
        
        st.session_state.final_pdf_bytes = pdf_buffer.getvalue()
        
        progress_bar.empty()
        status_text.success("🎉 全份文件處理完成！請點擊下方按鈕下載。")

# --- 獨立顯示下載按鈕 ---
if st.session_state.final_pdf_bytes is not None:
    st.download_button(
        label="📥 點我下載乾淨版 PDF",
        data=st.session_state.final_pdf_bytes,
        file_name="cleaned_document.pdf",
        mime="application/pdf"
    )