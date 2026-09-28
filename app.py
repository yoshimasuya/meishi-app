import os
import json
import pandas as pd
import streamlit as st
from pdf2image import convert_from_path
from google import genai
from google.genai import types

st.set_page_config(page_title="名刺PDF AI自動データ化ツール", layout="centered")
st.title("🎴 名刺PDF AI自動データ化ツール")
st.write("名刺PDFファイルをアップロードすると、AIが解析してExcelファイルに書き出します。")

# SecretsからAPIキーを取得
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Gemini APIキーが設定されていません。StreamlitのSecretsに設定してください。")
    st.stop()

client = genai.Client(api_key=api_key)

uploaded_file = st.file_uploader("名刺PDFファイルを選択してください", type=["pdf"])

if uploaded_file is not None:
    if st.button("データ抽出を開始する", type="primary"):
        with st.spinner("PDFを解析中... 少々お待ちください"):
            # 一時ファイルとして保存
            temp_pdf_path = "temp_input.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # PDFを画像に変換
            try:
                images = convert_from_path(temp_pdf_path, dpi=200)
            except Exception as e:
                st.error("PDFの画像変換に失敗しました。Popplerがインストールされているか確認してください。")
                st.stop()

            all_cards_data = []
            prompt = """
            画像に含まれるすべての名刺から以下の情報を抽出し、JSONフォーマットで出力してください。
            複数の名刺がある場合は配列（リスト）にして返してください。

            抽出項目:
            - company_name: 会社名（または店舗名）
            - title_and_name: 肩書・氏名
            - address: 住所
            - phone_number: 電話番号
            """

            for idx, img in enumerate(images):
                temp_img_path = f"temp_page_{idx}.png"
                img.save(temp_img_path, "PNG")

                with open(temp_img_path, "rb") as f:
                    image_bytes = f.read()

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                os.remove(temp_img_path)

                try:
                    data = json.loads(response.text)
                    if isinstance(data, list):
                        all_cards_data.extend(data)
                    elif isinstance(data, dict):
                        all_cards_data.append(data)
                except Exception as e:
                    st.warning(f"{idx+1}ページ目の解析中にエラーが発生しました。")

            os.remove(temp_pdf_path)

            if all_cards_data:
                df = pd.DataFrame(all_cards_data)
                df.columns = ["会社名（店舗名）", "肩書・氏名", "住所", "電話番号"]
                
                st.success(f"抽出成功！計 {len(all_cards_data)} 件のデータを抽出しました。")
                st.dataframe(df)

                # Excelダウンロード用の処理
                excel_output_path = "result.xlsx"
                df.to_excel(excel_output_path, index=False)

                with open(excel_output_path, "rb") as f:
                    st.download_button(
                        label="📥 Excelファイルをダウンロード",
                        data=f,
                        file_name="名刺リスト.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("データを抽出できませんでした。")