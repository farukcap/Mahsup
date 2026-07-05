import os
from flask import Flask, render_template, request, jsonify
import networkx as nx

app = Flask(__name__)

# Canlı simülasyon için geçici bellek veritabanları
AKTIF_KULLANICILAR = {}  # session_id -> {tc, tel, isim}
BEKLEYEN_BEYANLAR = []   # [{id, borclu_tc, borclu_isim, alacakli_tc, alacakli_isim, miktar}]
ONAYLANAN_BORCLAR = []   # [{borclu, alacakli, miktar}]

def optimize_debts(borclar):
    bakiyeler = {}
    for b in borclar:
        borclu = b['borclu'].strip().title()
        alacakli = b['alacakli'].strip().title()
        miktar = float(b['miktar'])
        bakiyeler[borclu] = bakiyeler.get(borclu, 0.0) - miktar
        bakiyeler[alacakli] = bakiyeler.get(alacakli, 0.0) + miktar
        
    borclular = []
    alacaklilar = []
    for kisi, bakiye in bakiyeler.items():
        if bakiye < -0.01: borclular.append({'isim': kisi, 'bakiye': abs(bakiye)})
        elif bakiye > 0.01: alacaklilar.append({'isim': kisi, 'bakiye': bakiye})
            
    net_odemeler = []
    i, j = 0, 0
    while i < len(borclular) and j < len(alacaklilar):
        b_kisi = borclular[i]
        a_kisi = alacaklilar[j]
        odenecek = min(b_kisi['bakiye'], a_kisi['bakiye'])
        net_odemeler.append({
            "gonderen": b_kisi['isim'],
            "alan": a_kisi['isim'],
            "miktar": round(odenecek, 2)
        })
        b_kisi['bakiye'] -= odenecek
        a_kisi['bakiye'] -= odenecek
        if b_kisi['bakiye'] < 0.01: i += 1
        if a_kisi['bakiye'] < 0.01: j += 1

    ozet = [{"isim": k, "bakiye": round(b, 2)} for k, b in bakiyeler.items()]
    return net_odemeler, ozet

@app.route('/')
def ana_sayfa():
    return render_template('index.html')

# 1. Kolpadan Giriş ve SMS Kod Gönderimi
@app.route('/api/auth/sms-gonder', methods=['POST'])
def sms_gonder():
    data = request.json
    # Kolpa SMS kodu üretimi
    return jsonify({"success": True, "mesaj": "Doğrulama kodu 1234 olarak gönderildi (Simülasyon)."})

# 2. Giriş Tamamlama
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    tc = data.get('tc')
    tel = data.get('tel')
    isim = data.get('isim').strip().title()
    sms_kod = data.get('kod')
    
    if sms_kod != "1234":
        return jsonify({"success": False, "hata": "Hatalı SMS kodu! (Test için 1234 giriniz)"})
        
    # Kullanıcıyı hafızaya kaydet (T.C. benzersiz anahtarımız)
    AKTIF_KULLANICILAR[tc] = {"tc": tc, "tel": tel, "isim": isim}
    return jsonify({"success": True, "kullanici": AKTIF_KULLANICILAR[tc]})

# 3. Borç Beyanı Yollama
@app.route('/api/beyan/gonder', methods=['POST'])
def beyan_gonder():
    data = request.json
    gonderen_tc = data.get('gonderen_tc')
    karsi_tc = data.get('karsi_tc')
    karsi_isim = data.get('karsi_isim').strip().title()
    miktar = float(data.get('miktar'))
    tip = data.get('tip') # 'borcluyum' veya 'alacakliyim'
    
    gonderen = AKTIF_KULLANICILAR.get(gonderen_tc)
    if not gonderen:
        return jsonify({"success": False, "hata": "Oturum geçersiz."})
        
    beyan_id = len(BEKLEYEN_BEYANLAR) + 1
    
    if tip == 'borcluyum':
        beyan = {
            "id": beyan_id,
            "borclu_tc": gonderen_tc, "borclu_isim": gonderen['isim'],
            "alacakli_tc": karsi_tc, "alacakli_isim": karsi_isim,
            "miktar": miktar, "durum": "Bekliyor"
        }
    else:
        beyan = {
            "id": beyan_id,
            "borclu_tc": karsi_tc, "borclu_isim": karsi_isim,
            "alacakli_tc": gonderen_tc, "alacakli_isim": gonderen['isim'],
            "miktar": miktar, "durum": "Bekliyor"
        }
        
    BEKLEYEN_BEYANLAR.append(beyan)
    return jsonify({"success": True, "mesaj": "Beyan karşı tarafa iletildi, onay bekleniyor."})

# 4. Kullanıcıya Gelen Bildirimleri Çekme (Poll)
@app.route('/api/beyan/listele/<tc>', methods=['GET'])
def beyan_listele(tc):
    # Kullanıcının onaylaması gereken (hedef olduğu) bekleyen beyanları filtrele
    gelenler = [b for b in BEKLEYEN_BEYANLAR if (b['borclu_tc'] == tc or b['alacakli_tc'] == tc) and b['durum'] == "Bekliyor"]
    return jsonify({"gelen_beyanlar": gelenler, "onaylanan_havuz": ONAYLANAN_BORCLAR})

# 5. Beyanı Onaylama
@app.route('/api/beyan/onayla', methods=['POST'])
def beyan_onayla():
    data = request.json
    beyan_id = int(data.get('id'))
    
    for b in BEKLEYEN_BEYANLAR:
        if b['id'] == beyan_id:
            b['durum'] = "Onaylandı"
            # Kesinleşen borç havuzuna aktar
            ONAYLANAN_BORCLAR.append({
                "borclu": b['borclu_isim'],
                "alacakli": b['alacakli_isim'],
                "miktar": b['miktar']
            })
            return jsonify({"success": True})
            
    return jsonify({"success": False, "hata": "Beyan bulunamadı."})

# 6. Algoritmayı Çalıştır (Konsolide Havuz Üzerinden)
@app.route('/api/algoritma/calistir', methods=['GET'])
def algoritma_calistir():
    if not ONAYLANAN_BORCLAR:
        return jsonify({"hata": "Onaylanmış finansal havuz boş."}), 400
        
    G = nx.DiGraph()
    for b in ONAYLANAN_BORCLAR:
        G.add_edge(b['borclu'], b['alacakli'], weight=float(b['miktar']))
        
    donguler = [" ➔ ".join(d) + " ➔ " + d[0] for d in nx.simple_cycles(G)]
    net_odemeler, genel_ozet = optimize_debts(ONAYLANAN_BORCLAR)
    
    return jsonify({
        "donguler": donguler,
        "net_odemeler": net_odemeler,
        "genel_ozet": genel_ozet,
        "analiz": {
            "toplam_brut": sum(b['miktar'] for b in ONAYLANAN_BORCLAR),
            "toplam_net": sum(n['miktar'] for n in net_odemeler)
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    app = app
