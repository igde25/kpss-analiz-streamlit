import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

# --- Sheets Sabitleri ---
SHEET_TITLE = '1jKUXQyvUpntbKwJtisw3_QHnWB0g1_diiYOArgcvaAk'
DERS_ARALIK_SAYFASI = 'DersAraliklari'
KONU_LISTESI_SAYFASI = 'KonuListesi'
VERI_GIRIS_SAYFASI = 'VeriGiris'
# ------------------------------------------------

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Streamlit Secrets kullanarak Sheets istemcisini yetkilendirir."""
    try:
        # secrets.toml dosyasındaki bilgileri kullanır.
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return gc
    except Exception as e:
        st.error(f"Sheets yetkilendirme hatası: Lütfen Servis Hesabı Secrets dosyanızı kontrol edin. Hata: {e}")
        return None

def get_data(ws_name):
    """Belirtilen sayfadan tüm veriyi çeker."""
    gc = get_gspread_client()
    if not gc:
        return pd.DataFrame() 

    try:
        spreadsheet = gc.open_by_key(SHEET_TITLE)
        ws = spreadsheet.worksheet(ws_name)
        # Sütun başlıklarını küçük harfe çevirme ve boşlukları kaldırma (Flask kodunuzdaki mantık)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"'{ws_name}' verisini çekerken hata: Sayfa adı Sheets'te bulunamadı veya yapısal hata var. Hata: {e}")
        return pd.DataFrame()

def save_data(payload):
    """Veriyi Sheets'e kaydeder."""
    gc = get_gspread_client()
    if not gc:
        st.error("Kaydetme işlemi başarısız: Sheets bağlantısı yok.")
        return False
        
    try:
        spreadsheet = gc.open_by_key(SHEET_TITLE)
        ws = spreadsheet.worksheet(VERI_GIRIS_SAYFASI)
        
        kayit_zamani = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        rows_to_append = []
        for kayit in payload['kayitlar']:
            row = [
                kayit_zamani,
                payload.get('denemeAdi', ''),
                payload.get('adSoyadi', ''),
                kayit.get('dersAdi', ''),
                kayit.get('konuAdi', ''),
                kayit.get('soruNo', ''),
                kayit.get('cevap', ''),
                kayit.get('durum', '')
            ]
            rows_to_append.append(row)
            
        ws.append_rows(rows_to_append)
        return True
    except Exception as e:
        st.error(f"Veri kaydı sırasında kritik hata oluştu: {e}")
        return False

# --- Streamlit Arayüzü ---

st.set_page_config(page_title="KPSS Analiz Sistemi", layout="centered")
st.title("📚 KPSS Analiz Sistemi Veri Girişi")

# Verileri çekme
ders_araliklari_df = get_data(DERS_ARALIK_SAYFASI)
konu_listesi_df = get_data(KONU_LISTESI_SAYFASI)

if ders_araliklari_df.empty or konu_listesi_df.empty:
    st.warning("Veri yüklenemedi. Lütfen Sheets bağlantınızı ve sayfa isimlerini kontrol edin.")
    st.stop()
    
# Sütun isimlerini küçültme ve boşlukları kaldırma
ders_araliklari_df.columns = [c.lower().replace(' ', '') for c in ders_araliklari_df.columns]
konu_listesi_df.columns = [c.lower().replace(' ', '') for c in konu_listesi_df.columns]

# --- Sayfa Durumu Yönetimi ---
if 'page' not in st.session_state:
    st.session_state.page = 'info'
if 'kayitlar' not in st.session_state:
    st.session_state.kayitlar = {}
    
def go_to_subject_selection(ad_soyadi, deneme_adi):
    """Temel bilgileri kaydeder ve sonraki sayfaya geçer."""
    if not ad_soyadi or not deneme_adi:
        st.error("Lütfen Ad Soyadı ve Deneme Adı alanlarını doldurun.")
        return
        
    st.session_state.ad_soyadi = ad_soyadi
    st.session_state.deneme_adi = deneme_adi
    st.session_state.page = 'subject'

def go_to_info_page():
    st.session_state.page = 'info'
    st.session_state.kayitlar = {}

# --- Arayüz Bölümleri ---

if st.session_state.page == 'info':
    st.subheader("📝 Temel Bilgiler")
    
    # Session state'i kullanarak formu temiz tutma
    if 'ad_soyadi_val' not in st.session_state:
        st.session_state.ad_soyadi_val = ''
    if 'deneme_adi_val' not in st.session_state:
        st.session_state.deneme_adi_val = ''
        
    with st.form("basic_info_form"):
        ad_soyadi = st.text_input("Ad Soyadı", key="ad_soyadi_input", value=st.session_state.ad_soyadi_val)
        deneme_adi = st.text_input("Deneme Adı", key="deneme_adi_input", value=st.session_state.deneme_adi_val)
        
        submitted = st.form_submit_button("İlerle")
        if submitted:
            st.session_state.ad_soyadi_val = ad_soyadi
            st.session_state.deneme_adi_val = deneme_adi
            go_to_subject_selection(ad_soyadi, deneme_adi)
            st.rerun()

elif st.session_state.page == 'subject':
    st.subheader(f"Ders Seçimi: {st.session_state.deneme_adi}")
    
    ders_options = ders_araliklari_df['ders'].tolist()
    
    selected_ders = st.selectbox("Ders Seçin", options=['---'] + ders_options, key="ders_secim_input")

    if selected_ders and selected_ders != '---':
        ders_info = ders_araliklari_df[ders_araliklari_df['ders'] == selected_ders].iloc[0]
        start_soru = int(ders_info['baslangic'])
        end_soru = int(ders_info['bitis'])
        
        st.markdown(f"**{selected_ders}** için Soru Aralığı: {start_soru} - {end_soru}")

        ilgili_konular = konu_listesi_df[konu_listesi_df['ders'] == selected_ders]['konu adı'].tolist()
        konu_options = [''] + ilgili_konular
        
        # Soru giriş formunu oluşturma
        with st.form(key='soru_giris_form', clear_on_submit=False):
            st.caption("Cevapları ve Konuları Girin:")
            
            kayitlar_current = st.session_state.kayitlar.get(selected_ders, {})
            soru_kayitlari = []
            
            for i in range(start_soru, end_soru + 1):
                col1, col2, col3 = st.columns([1, 3, 2])
                
                with col1:
                    st.write(f"Soru {i}:")
                
                with col2:
                    varsayilan_konu = kayitlar_current.get(i, {}).get('konu', '')
                    konu_secim = st.selectbox("Konu Seçin", options=konu_options, index=konu_options.index(varsayilan_konu) if varsayilan_konu in konu_options else 0, label_visibility="collapsed", key=f"konu_{selected_ders}_{i}")
                
                with col3:
                    cevap_options = ['', 'Doğru (D)', 'Yanlış (Y)', 'Boş (B)']
                    cevap_secim_str = st.selectbox("Cevap", options=cevap_options, label_visibility="collapsed", key=f"cevap_{selected_ders}_{i}")
                
                if cevap_secim_str and cevap_secim_str != '':
                    cevap_kisa = cevap_secim_str[cevap_secim_str.find("(")+1:cevap_secim_str.find(")")].strip()
                    durum = cevap_secim_str[:cevap_secim_str.find("(")].strip()
                    
                    kayitlar_current[i] = {
                        'dersAdi': selected_ders,
                        'konuAdi': konu_secim if konu_secim else '',
                        'soruNo': i,
                        'cevap': cevap_kisa,
                        'durum': durum
                    }
                    soru_kayitlari.append(kayitlar_current[i])
            
            submitted_soru = st.form_submit_button("Cevapları Kaydet ve Bitir", type="primary")
            
            if submitted_soru:
                if not soru_kayitlari:
                    st.error("Kaydedilecek cevap bulunamadı. Lütfen en az bir soru için cevap girin.")
                else:
                    payload = {
                        'adSoyadi': st.session_state.ad_soyadi_val,
                        'denemeAdi': st.session_state.deneme_adi_val,
                        'kayitlar': soru_kayitlari
                    }
                    
                    if save_data(payload):
                        st.success("Veriler Sheets'e başarıyla kaydedildi!")
                        # Başarıyla kaydedilirse temel bilgileri temizle
                        st.session_state.ad_soyadi_val = ''
                        st.session_state.deneme_adi_val = ''
                        go_to_info_page()
                        st.rerun()
                    else:
                        st.error("Veri kaydı başarısız oldu. Yetkilendirmeyi kontrol edin.")
        
        # Geri butonu
        if st.button("⬅️ Temel Bilgilere Geri Dön"):
            go_to_info_page()
            st.rerun()
