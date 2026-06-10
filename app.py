# =============================================================
# BIP210 - Gezi Rehberi Streamlit Arayüzü
# Yazar: [Adınız Soyadınız] - [Öğrenci Numaranız]
# Açıklama: Strapi'den mekan verilerini çeker; şehir, dil ve
# puan filtresiyle modern kart düzeninde listeler.
# =============================================================

import streamlit as st
import requests
import html

st.set_page_config(page_title="🌍 Gezi Rehberi", page_icon="", layout="wide")

BASE_URL = "https://rehber.onrender.com"

# ─── CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
.kart-icerik {
    background:#1e1e2e; border-radius:0 0 12px 12px;
    padding:14px; margin-bottom:4px;
}
.kart h3 { color:#cdd6f4; margin:0 0 6px 0; font-size:1.05rem; }
.badge {
    display:inline-block; border-radius:20px; padding:2px 10px;
    font-size:.78rem; font-weight:bold; margin:2px;
}
.puan   { background:#a6e3a1; color:#1e1e2e; }
.sehir  { background:#89b4fa; color:#1e1e2e; }
.sirket { background:#cba6f7; color:#1e1e2e; }
.acik   { color:#bac2de; font-size:.85rem; line-height:1.6; margin-top:8px; }
.tam    { color:#cdd6f4; font-size:.88rem; line-height:1.7; margin-top:8px; }
            .yatay-kart {
    display: flex;
    background: #1e1e2e;
    border-radius: 18px;
    overflow: hidden;
    margin-bottom: 22px;
    border: 1px solid rgba(205, 214, 244, 0.08);
    box-shadow: 0 8px 24px rgba(0,0,0,0.22);
}

.yatay-resim {
    width: 310px;
    min-width: 310px;
    height: 220px;
    object-fit: cover;
}

.yatay-icerik {
    padding: 22px 24px;
    flex: 1;
}

.yatay-icerik h3 {
    color: #ffffff;
    margin: 0 0 12px 0;
    font-size: 1.55rem;
    line-height: 1.25;
}

.yatay-aciklama {
    color: #cdd6f4;
    font-size: 0.95rem;
    line-height: 1.7;
    margin-top: 12px;
}

@media (max-width: 900px) {
    .yatay-kart {
        flex-direction: column;
    }

    .yatay-resim {
        width: 100%;
        min-width: 100%;
        height: 240px;
    }
}
</style>
""", unsafe_allow_html=True)

st.title(" Gezi Rehberi")
st.caption("")
st.divider()


# =============================================================
# VERİ ÇEKME
# =============================================================
@st.cache_data(ttl=60)
def mekanlari_getir(locale="tr"):
    """
    Strapi'den tüm mekanları populate=* ile çeker.
    locale parametresiyle TR veya EN içerik alınır.
    """
    try:
        url = (
            f"{BASE_URL}/api/mekans"
            f"?populate=*&locale={locale}&pagination[pageSize]=100"
        )
        r = requests.get(url, timeout=20)
        if r.ok:
            return r.json().get("data", [])
        st.error(f"Sunucu hatası: {r.status_code}")
        return []
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")
        return []


def attr(mekan):
    """Strapi v4/v5 uyumlu attribute çekici."""
    return mekan.get("attributes", mekan)


def iliski_adi(a, alan, ad_field):
    """Relation alanından metin döner (v4 ve v5 uyumlu)."""
    iliski = a.get(alan)
    if not iliski:
        return None
    if isinstance(iliski, dict):
        data = iliski.get("data")
        if data and isinstance(data, dict):
            return (data.get("attributes") or data).get(ad_field)
        return iliski.get(ad_field)
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def gorsel_erisebilir_mi(url):
    """Görsel URL'si gerçekten image/* dönüyor mu kontrol eder."""
    if not url:
        return False

    try:
        r = requests.head(url, timeout=6, allow_redirects=True)
        content_type = r.headers.get("Content-Type", "")
        if r.ok and content_type.startswith("image/"):
            return True
        if r.status_code not in (403, 405):
            return False
    except requests.RequestException:
        pass

    try:
        r = requests.get(
            url,
            headers={"Range": "bytes=0-2048"},
            stream=True,
            timeout=8,
            allow_redirects=True,
        )
        content_type = r.headers.get("Content-Type", "")
        return r.ok and content_type.startswith("image/")
    except requests.RequestException:
        return False


def resim_url(a):
    """
    Kapak_Resmi alanından görsel URL'si döner.
    Strapi v5: liste veya tekil obje formatını destekler.
    Görsel yoksa veya Strapi'deki dosya 404 ise mekan adına göre
    farklı Unsplash yedek verir.
    """
    adi   = a.get("Mekan_Adi", "gezi")
    kapak = a.get("Kapak_Resmi")

    # Strapi upload dosyası Render'da silinirse kırık ikon yerine
    # mekan adına göre sabit ama farklı bir yedek görsel göster.
    fallback_seed = sum(ord(c) for c in adi) % 100000
    fallback = f"https://picsum.photos/seed/mekan-{fallback_seed}/800/500"

    if not kapak:
        return fallback

    url = ""

    # Strapi v5: direkt liste [{"url": "...", ...}]
    if isinstance(kapak, list) and len(kapak) > 0:
        ilk = kapak[0]
        if isinstance(ilk, dict):
            url = ilk.get("url", "")

    # Strapi v5: tek obje {"url": "..."}
    elif isinstance(kapak, dict) and "url" in kapak:
        url = kapak.get("url", "")

    # Strapi v4: {"data": [{"attributes": {"url": "..."}}]}
    elif isinstance(kapak, dict) and "data" in kapak:
        data = kapak["data"]
        if isinstance(data, list) and len(data) > 0:
            url = (data[0].get("attributes") or data[0]).get("url", "")
        elif isinstance(data, dict):
            url = (data.get("attributes") or data).get("url", "")

    if not url:
        return fallback

    # Göreceli URL'yi tam URL'ye çevir
    tam_url = url if url.startswith("http") else f"{BASE_URL}{url}"
    return tam_url if gorsel_erisebilir_mi(tam_url) else fallback
# =============================================================
# SIDEBAR – FİLTRELER
# =============================================================
st.sidebar.header("🔍 Filtreler")

# 1. Dil seçimi — varsayılan Türkçe
dil = st.sidebar.radio(
    "İçerik Dili:",
    ["tr", "en"],
    index=0,  # 0 = tr varsayılan
    format_func=lambda x: "🇹🇷 Türkçe" if x == "tr" else "🇬🇧 English"
)

# Seçilen dile göre mekanları çek
mekanlar = mekanlari_getir(dil)

# TR boş gelirse EN'e düş (Strapi varsayılan dil EN ise)
if not mekanlar and dil == "tr":
    mekanlar = mekanlari_getir("en")

if not mekanlar:
    st.warning("⚠️ Henüz mekan eklenmemiş veya sunucuya ulaşılamıyor.")
    st.info("💡 `python main_bot.py` komutuyla mekanları otomatik ekleyebilirsiniz.")
    st.stop()

# 2. Şehir filtresi — mekan verisinden topla
sehir_seti = set()
for m in mekanlar:
    a = attr(m)
    s = iliski_adi(a, "sehir", "Ad")
    if s:
        sehir_seti.add(s)

# main_bot'taki 10 şehir sırası korunsun
SEHIR_SIRASI = [
    "San Francisco", "Tokyo", "Berlin", "Londra", "Seul",
    "Singapur", "Şangay", "Amsterdam", "Dubai", "İstanbul"
]
sirali_sehirler = [s for s in SEHIR_SIRASI if s in sehir_seti]
# Listede olmayan ek şehirler varsa sona ekle
sirali_sehirler += sorted(sehir_seti - set(SEHIR_SIRASI))
sehir_listesi = ["Tümü"] + sirali_sehirler

secilen_sehir = st.sidebar.selectbox("Şehir:", sehir_listesi)

# 3. Min puan filtresi
min_puan = st.sidebar.slider("Min Puan:", 0.0, 10.0, 0.0, 0.5)


# =============================================================
# FİLTRELEME
# =============================================================
filtreli = []
for m in mekanlar:
    a         = attr(m)
    sehir_adi = iliski_adi(a, "sehir", "Ad") or "Bilinmiyor"
    puan      = float(a.get("Puan") or 0)

    if secilen_sehir != "Tümü" and sehir_adi != secilen_sehir:
        continue
    if puan < min_puan:
        continue
    filtreli.append(m)


# =============================================================
# İSTATİSTİK SATIRI
# =============================================================
c1, c2, c3 = st.columns(3)
c1.metric("Toplam Mekan", len(mekanlar))
c2.metric("Gösterilen",   len(filtreli))
c3.metric("Şehir",        secilen_sehir)
st.divider()

if not filtreli:
    st.warning("Bu filtreye uygun mekan bulunamadı.")
    st.stop()


# =============================================================
# KART IZGARA GÖRÜNÜMÜ
# "Devamını Oku" butonu ile tam makale gösterimi
# =============================================================

# Hangi mekanın açık olduğunu session_state ile takip et
if "acik_mekan" not in st.session_state:
    st.session_state.acik_mekan = None

for i, m in enumerate(filtreli):
    a          = attr(m)
    adi        = a.get("Mekan_Adi",  "İsimsiz")
    aciklama   = a.get("Aciklama",   "") or ""
    puan       = float(a.get("Puan", 0) or 0)
    sehir_adi  = iliski_adi(a, "sehir",  "Ad")         or "–"
    sirket_adi = iliski_adi(a, "sirket", "Sirket_Adi") or None
    gorsel     = resim_url(a)

    mekan_id = m.get("id") or m.get("documentId") or i
    acik_mi = st.session_state.acik_mekan == mekan_id

    ozet = aciklama if acik_mi else (
        aciklama[:420] + "…" if len(aciklama) > 420 else aciklama
    )

    with st.container():
        sol, sag = st.columns([1.1, 2.4], gap="large")

        with sol:
            st.image(gorsel, use_container_width=True)

        with sag:
            st.markdown(f"### {adi}")

            rozet = f"⭐ **{puan}** &nbsp;&nbsp; 📍 **{sehir_adi}**"
            if sirket_adi:
                rozet += f" &nbsp;&nbsp; 🏢 **{sirket_adi}**"

            st.markdown(rozet)
            st.write(ozet)

            if len(aciklama) > 420:
                buton_yazi = "🔼 Kapat" if acik_mi else "📖 Devamını Oku"
                if st.button(buton_yazi, key=f"btn_{mekan_id}"):
                    st.session_state.acik_mekan = None if acik_mi else mekan_id
                    st.rerun()

    st.divider()
# ─── Alt Bilgi ──────────────────────────────────────────────
st.markdown(
    "<p style='text-align:center;color:#585b70;margin-top:30px'>"
    "BIP210 Final Projesi · YZ Destekli Gezi Rehberi · Streamlit + Strapi</p>",
    unsafe_allow_html=True
)
