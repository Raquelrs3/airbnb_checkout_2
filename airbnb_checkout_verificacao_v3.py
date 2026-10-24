"""
App de Check-out – Verificação do Apartamento (Airbnb)

Fluxo em etapas (uma tela por ambiente), pensado para celular e computador:
    Identificação → Quartos → Sala → Banheiros → Lavabo → Rouparia → Cozinha
    → Finalização → Histórico

- Registro salvo no Google Sheets (aba "checkouts")
- Fotos salvas no Google Drive, numa subpasta por check-out:
      <PASTA_RAIZ>/2026-10-23_Citta_Residence/2026-10-23_Citta_Residence_Quarto_1_01.jpg

Arquivos do projeto: app.py, design.css, requirements.txt, .streamlit/config.toml (tema)
"""

import io
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from PIL import Image, ImageOps

st.set_page_config(page_title="Check-out Apartamento", page_icon=":material/home_work:",
                   layout="wide", initial_sidebar_state="auto")

# ======================================================================
# CONFIGURAÇÃO (edite aqui para mudar apartamentos, itens e estoques)
# ======================================================================
FUSO = ZoneInfo("America/Sao_Paulo")  # o servidor do Streamlit Cloud roda em UTC
ABA_CHECKOUTS = "checkouts"
PASTA_FOTOS_PADRAO = "1zB9XyrqfGXvjX6N9QDvABAnIuddKQsjb"  # pode ser sobrescrita em secrets
TORNAR_FOTOS_PUBLICAS = False  # True = qualquer pessoa com o link vê a foto
TIPOS_FOTO = ["jpg", "jpeg", "png"]
LADO_MAX_FOTO = 1600  # px — fotos do celular são reduzidas para subir mais rápido

APARTAMENTOS = ["Citta Residence", "Vista Park"]

# Cada cômodo tem grupos de itens (os grupos só organizam a tela)
COMODOS = [
    {"chave": "q1", "titulo": "Quarto 1", "icone": "bed", "grupos": {
        "Móveis e eletrônicos": ["Cama", "Colchão", "Armário", "Prateleiras",
                                 "Televisão", "Controle da TV", "Ventilador"],
        "Utilidades": ["Ferro de passar", "Tapete de passar", "Cabide"],
        "Estrutura": ["Paredes", "Chão", "Janela", "Cortinas", "Iluminação"]}},
    {"chave": "q2", "titulo": "Quarto 2", "icone": "bed", "grupos": {
        "Móveis e eletrônicos": ["Cama", "Colchão", "Prateleiras", "Ventilador"],
        "Estrutura": ["Paredes", "Janela", "Cortinas", "Iluminação"]}},
    {"chave": "sala", "titulo": "Sala", "icone": "weekend", "grupos": {
        "Móveis": ["Sofá", "Capa do sofá", "Mesa", "Cadeiras da mesa",
                   "Cadeiras do balcão", "Vidro do Balcão", "Rack TV"],
        "Eletrônicos": ["Televisão", "Controles TV", "Aparelho da Claro/net",
                        "Aparelho Branco (Gateway)", "DVD's"],
        "Decoração e lazer": ["Jogo americano", "Quadros", "Taco de sinuca",
                              "Suporte taco de sinuca"],
        "Estrutura": ["Papel de parede", "Paredes", "Cortina", "Chão", "Iluminação"]}},
    {"chave": "b1", "titulo": "Banheiro 1", "icone": "shower", "grupos": {
        "Louças e metais": ["Vaso sanitário", "Descarga", "Chuveiro", "Box", "Pia",
                            "Espelho"],
        "Acessórios": ["Suporte xampu", "Suporte sabonete", "Dispenser sabonete",
                       "Dispenser xampu e condicionador", "Lixeira"],
        "Enxoval": ["Toalha de banho", "Toalha de rosto", "Tapete"],
        "Estrutura": ["Paredes", "Chão", "Iluminação", "Exaustor"]}},
    {"chave": "b2", "titulo": "Banheiro 2", "icone": "shower", "grupos": {
        "Louças e metais": ["Vaso sanitário", "Descarga", "Chuveiro", "Box", "Pia",
                            "Espelho"],
        "Acessórios": ["Suporte xampu", "Suporte sabonete", "Dispenser sabonete",
                       "Dispenser xampu e condicionador", "Lixeira"],
        "Enxoval": ["Toalha de banho", "Toalha de rosto", "Tapete"],
        "Estrutura": ["Paredes", "Iluminação", "Exaustor"]}},
    {"chave": "lavabo", "titulo": "Lavabo", "icone": "wc", "grupos": {
        "Louças e metais": ["Vaso sanitário", "Descarga", "Pia", "Espelho"],
        "Acessórios": ["Dispenser sabonete", "Toalha de mão", "Lixeira", "Quadro"],
        "Estrutura": ["Paredes", "Chão", "Iluminação", "Exaustor"]}},
]

ESTOQUE_ROUPARIA = {
    "Toalha de banho": {"qtd": 9, "valor": 45},
    "Toalha de rosto grossas": {"qtd": 6, "valor": 25},
    "Toalha de rosto finas": {"qtd": 9, "valor": 25},
    "Toalha de piscina": {"qtd": 9, "valor": 45},
    "Tapete banheiro": {"qtd": 4, "valor": 35},
    "Roupa de cama solteiro": {"qtd": 3, "valor": 120},
    "Roupa de cama casal": {"qtd": 3, "valor": 120},
    "Roupa de cama queen": {"qtd": 3, "valor": 120},
    "Cobertor": {"qtd": 5, "valor": 120},
    "Travesseiros": {"qtd": 8, "valor": 120},
}

COZINHA = {
    "Talheres e louças": ["Facas", "Garfos", "Colheres", "Colheres de chá", "Copos",
                          "Xícaras", "Pratos", "Petisqueiras", "Tigelas verdes",
                          "Saladeira", "Refratário de forno", "Tigela de cozinhar ovo azul"],
    "Utensílios": ["Ralador", "Escorredor", "Tábua de carne", "Cesta de cozimento a vapor",
                   "Porta-mantimentos", "Lixeira pequena"],
    "Eletroportáteis": ["Cafeteira", "Purificador de água", "Mixer"],
    "Panos": ["Pano de prato", "Pano de chão"],
}

PANELAS = ["Panela grande", "Panela média", "Caçarola", "Frigideira", "Leiteira"]
ESTADOS_PANELAS = ["Bom estado", "Riscada", "Cabo solto", "Amassada",
                   "Muito queimada", "Inutilizável"]

# Etapas do fluxo (ordem da navegação)
ETAPAS = (
    [{"id": "ident", "titulo": "Identificação", "icone": "badge", "secao": "Início"}]
    + [{"id": c["chave"], "titulo": c["titulo"], "icone": c["icone"], "secao": "Ambientes"}
       for c in COMODOS]
    + [{"id": "rouparia", "titulo": "Rouparia", "icone": "local_laundry_service",
        "secao": "Inventário"},
       {"id": "cozinha", "titulo": "Cozinha", "icone": "kitchen", "secao": "Inventário"},
       {"id": "final", "titulo": "Finalização", "icone": "task_alt", "secao": "Fechamento"},
       {"id": "hist", "titulo": "Histórico", "icone": "history", "secao": "Consulta"}]
)
IDX = {e["id"]: i for i, e in enumerate(ETAPAS)}
N_FLUXO = IDX["final"] + 1  # etapas contadas no progresso (sem o Histórico)
COMODO_POR_CHAVE = {c["chave"]: c for c in COMODOS}


# ======================================================================
# UTILITÁRIOS
# ======================================================================
def slug(texto: str) -> str:
    """'Citta Residence' -> 'Citta_Residence' (sem acentos/espaços)."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")


def itens_do_comodo(comodo):
    return [i for itens in comodo["grupos"].values() for i in itens]


def itens_cozinha():
    return [i for itens in COZINHA.values() for i in itens]


def reais(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar_css():
    caminho = Path(__file__).parent / "design.css"
    if caminho.exists():
        st.markdown(f"<style>{caminho.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)


def colorir_faltante(valor):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return ""
    return "color: #3B6D11; font-weight: 600;" if n == 0 else "color: #A32D2D; font-weight: 600;"


# ======================================================================
# GOOGLE SHEETS / DRIVE  (camada de dados — trocar só aqui numa migração)
# ======================================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]


@st.cache_resource
def credenciais_service_account():
    return SACredentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES)


@st.cache_resource
def conectar_planilha():
    client = gspread.authorize(credenciais_service_account())
    if "planilha_id" in st.secrets:
        planilha = client.open_by_key(st.secrets["planilha_id"])
    else:
        planilha = client.open("Historico_Checkout")
    try:
        return planilha.worksheet(ABA_CHECKOUTS)
    except gspread.WorksheetNotFound:
        return planilha.add_worksheet(ABA_CHECKOUTS, rows=1000, cols=200)


@st.cache_resource
def conectar_drive():
    """
    Contas de serviço não têm cota no Drive pessoal ('storageQuotaExceeded').
    Com [drive_oauth] nos secrets, as fotos sobem com a SUA conta Google.
    """
    if "drive_oauth" in st.secrets:
        cfg = st.secrets["drive_oauth"]
        creds = UserCredentials(
            token=None,
            refresh_token=cfg["refresh_token"],
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/drive"],
        )
    else:
        creds = credenciais_service_account()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def pasta_raiz_fotos():
    return st.secrets.get("drive_pasta_id", PASTA_FOTOS_PADRAO)


def obter_ou_criar_pasta(service, nome, pasta_pai):
    nome_q = nome.replace("'", "\\'")
    q = (f"name = '{nome_q}' and '{pasta_pai}' in parents and "
         "mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    r = service.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                             includeItemsFromAllDrives=True).execute()
    if r.get("files"):
        return r["files"][0]["id"]
    pasta = service.files().create(
        body={"name": nome, "mimeType": "application/vnd.google-apps.folder",
              "parents": [pasta_pai]},
        fields="id", supportsAllDrives=True).execute()
    return pasta["id"]


def enviar_fotos(service, fotos, pasta_id, prefixo):
    """fotos = lista de dicts {"nome", "tipo", "dados"} guardados na sessão."""
    links = []
    for i, foto in enumerate(fotos, start=1):
        ext = "jpg" if foto["tipo"] == "image/jpeg" else foto["nome"].rsplit(".", 1)[-1].lower()
        media = MediaIoBaseUpload(io.BytesIO(foto["dados"]), mimetype=foto["tipo"])
        arquivo = service.files().create(
            body={"name": f"{prefixo}_{i:02d}.{ext}", "parents": [pasta_id]},
            media_body=media, fields="id", supportsAllDrives=True).execute()
        if TORNAR_FOTOS_PUBLICAS:
            service.permissions().create(
                fileId=arquivo["id"], body={"role": "reader", "type": "anyone"},
                supportsAllDrives=True).execute()
        links.append(f"https://drive.google.com/file/d/{arquivo['id']}/view")
    return " | ".join(links)


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_foto(file_id):
    """Baixa a imagem pela API (o link /view abre uma página HTML, não a imagem)."""
    buffer = io.BytesIO()
    req = conectar_drive().files().get_media(fileId=file_id, supportsAllDrives=True)
    downloader = MediaIoBaseDownload(buffer, req)
    concluido = False
    while not concluido:
        _, concluido = downloader.next_chunk()
    return buffer.getvalue()


@st.cache_data(ttl=60, show_spinner=False)
def carregar_historico():
    valores = conectar_planilha().get_all_values()
    if len(valores) < 2:
        return pd.DataFrame()
    return pd.DataFrame(valores[1:], columns=valores[0])


def salvar_registro(registro):
    """Grava a linha respeitando a ordem do cabeçalho; colunas novas são adicionadas."""
    aba = conectar_planilha()
    cabecalho = aba.row_values(1)
    novas = [c for c in registro if c not in cabecalho]
    if novas:
        cabecalho = cabecalho + novas
        if len(cabecalho) > aba.col_count:
            aba.add_cols(len(cabecalho) - aba.col_count)
        aba.update(values=[cabecalho], range_name="A1")
    linha = [registro.get(c, "") for c in cabecalho]
    aba.append_row(linha, value_input_option="RAW", table_range="A1")


# ======================================================================
# ESTADO DA SESSÃO
# ======================================================================
# Widgets cujas chaves começam com "w_" guardam respostas. O Streamlit apaga o
# valor de um widget quando ele não aparece na tela; como mostramos uma etapa
# por vez, reatribuímos essas chaves a cada execução para não perder nada.
ss = st.session_state


def iniciar_estado():
    if ss.pop("limpar_formulario", False):
        for k in list(ss.keys()):
            if k != "mensagem_sucesso":
                del ss[k]
    for k in [k for k in ss.keys() if str(k).startswith("w_")]:
        ss[k] = ss[k]
    ss.setdefault("etapa", 0)
    ss.setdefault("fotos", {})      # grupo -> lista de fotos
    ss.setdefault("up_ver", {})     # grupo -> versão do uploader (para limpá-lo)
    ss.setdefault("w_data", date.today())
    ss.setdefault("w_apartamento", APARTAMENTOS[0])
    ss.setdefault("w_liberado", "Sim")


def ir_para(i):
    ss.etapa = max(0, min(i, len(ETAPAS) - 1))


def ir_para_pelo_menu(i):
    ir_para(i)
    ss._fechar_menu = ss.get("_fechar_menu_n", 0) + 1
    ss._fechar_menu_n = ss._fechar_menu


def conferidos(comodo):
    return [i for i in itens_do_comodo(comodo) if ss.get(f"w_{comodo['chave']}_{i}")]


def data_str():
    return ss.w_data.isoformat()


def apartamento():
    return ss.get("w_apartamento") or APARTAMENTOS[0]


# ---- fotos -----------------------------------------------------------
def reduzir_foto(arquivo):
    """Corrige a rotação do celular e reduz para LADO_MAX_FOTO (JPEG)."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(arquivo.getvalue())))
        img.thumbnail((LADO_MAX_FOTO, LADO_MAX_FOTO))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82, optimize=True)
        nome = arquivo.name.rsplit(".", 1)[0] + ".jpg"
        return {"nome": nome, "tipo": "image/jpeg", "dados": buf.getvalue()}
    except Exception:  # noqa: BLE001 — se não der para reduzir, guarda o original
        return {"nome": arquivo.name, "tipo": arquivo.type, "dados": arquivo.getvalue()}


def chave_uploader(grupo):
    return f"up_{grupo}_{ss.up_ver.get(grupo, 0)}"


def adicionar_fotos(grupo):
    novos = ss.get(chave_uploader(grupo)) or []
    ss.fotos.setdefault(grupo, []).extend(reduzir_foto(f) for f in novos)
    ss.up_ver[grupo] = ss.up_ver.get(grupo, 0) + 1  # limpa o campo de upload


def remover_foto(grupo, i):
    ss.fotos[grupo].pop(i)


# ======================================================================
# COMPONENTES VISUAIS
# ======================================================================
def executar_js(codigo, chave):
    """Roda um trecho de JavaScript na página do app (via iframe invisível).
    Dentro do código, use d = documento do app e w = janela do app."""
    with st.sidebar:  # no fim do menu, para não abrir espaço na tela principal
        st.markdown("<style>[class*='st-key-js-']{display:none !important}</style>",
                    unsafe_allow_html=True)
        with st.container(key=f"js-{chave}"):
            st.iframe(f"<script>const w=window.parent,d=w.document;{codigo}</script>",
                      height=1)


def rolar_para_o_topo():
    """Ao trocar de etapa, volta ao topo (no celular o botão Próximo fica no fim)."""
    if ss.get("_etapa_renderizada") != ss.etapa:
        ss._etapa_renderizada = ss.etapa
        executar_js(
            f"/*{ss.etapa}*/const m=d.querySelector('[data-testid=\"stMain\"]');"
            "if(m){m.scrollTo({top:0});}w.scrollTo({top:0});", "topo")


def fechar_menu_no_celular():
    """No celular (tela até 640px), fecha o menu lateral depois de escolher um ambiente.
    Aciona o próprio botão de recolher do Streamlit; no computador não faz nada."""
    n = ss.pop("_fechar_menu", None)
    if n is None:
        return
    executar_js(
        f"/*{n}*/if(w.matchMedia('(max-width: 640px)').matches){{"
        "let t=0;const f=()=>{"
        "const b=d.querySelector('button[aria-label=\"Collapse sidebar\"]');"
        "if(b){if(b.getAttribute('aria-expanded')!=='false'){b.click();}}"
        "else if(t++<10){setTimeout(f,100);}};setTimeout(f,50);}", "menu")


def cabecalho(etapa):
    if etapa["id"] == "hist":
        sub, titulo = "Consulta", "Histórico de check-outs"
        progresso, rotulo = None, ""
    elif etapa["id"] == "ident":
        sub, titulo = "Novo check-out", "Identificação"
        progresso, rotulo = 1 / N_FLUXO, f"Etapa 1 de {N_FLUXO}"
    else:
        sub = "Check-out em andamento"
        titulo = f"{apartamento()} · {ss.w_data:%d/%m/%Y}"
        n = IDX[etapa["id"]] + 1
        progresso, rotulo = n / N_FLUXO, f"Etapa {n} de {N_FLUXO} · {etapa['titulo']}"
    barra = ""
    if progresso is not None:
        barra = (f'<div class="ck-prog"><div class="ck-prog-fill" '
                 f'style="width:{progresso * 100:.0f}%"></div></div>'
                 f'<div class="ck-prog-txt">{rotulo}</div>')
    st.markdown(f'<div class="ck-head"><div class="ck-sub">{sub}</div>'
                f'<div class="ck-title">{titulo}</div>{barra}</div>',
                unsafe_allow_html=True)


def titulo_cartao(icone, titulo, direita="", descricao=""):
    st.markdown(
        f'<div class="ck-card-head"><span class="ck-icon">{icone}</span>'
        f'<span class="ck-card-title">{titulo}</span>'
        f'<span class="ck-card-count">{direita}</span></div>'
        + (f'<div class="ck-card-desc">{descricao}</div>' if descricao else ""),
        unsafe_allow_html=True)


def rotulo_grupo(texto):
    st.markdown(f'<div class="ck-group">{texto}</div>', unsafe_allow_html=True)


def bloco_fotos(grupo, titulo):
    fotos = ss.fotos.get(grupo, [])
    rotulo = f"Fotos ({len(fotos)})" if fotos else "Fotos"
    with st.expander(rotulo, icon=":material/photo_camera:"):
        st.file_uploader(f"Adicionar fotos – {titulo}", type=TIPOS_FOTO,
                         accept_multiple_files=True, key=chave_uploader(grupo),
                         on_change=adicionar_fotos, args=(grupo,),
                         label_visibility="collapsed")
        if fotos:
            with st.container(key=f"grade-fotos-{grupo}"):
                for i, foto in enumerate(fotos):
                    with st.container(key=f"foto-{grupo}-{i}"):
                        st.image(foto["dados"], width="stretch")
                        st.button("Remover", key=f"rm_{grupo}_{i}", icon=":material/delete:",
                                  type="tertiary", on_click=remover_foto, args=(grupo, i))


def navegacao(etapa, rotulo_proximo=None, desabilitar_proximo=False):
    i = IDX[etapa["id"]]
    with st.container(key="nav-rodape", horizontal=True):
        if i > 0:
            st.button("Voltar", icon=":material/arrow_back:", key="nav_voltar",
                      on_click=ir_para, args=(i - 1,), width="stretch")
        if i < IDX["final"]:
            prox = rotulo_proximo or f"Próximo: {ETAPAS[i + 1]['titulo']}"
            st.button(prox, icon=":material/arrow_forward:", icon_position="right",
                      key="nav_proximo", type="primary", width="stretch",
                      on_click=ir_para, args=(i + 1,), disabled=desabilitar_proximo)


def menu_lateral(atual):
    with st.sidebar:
        st.markdown('<div class="ck-brand"><span class="ck-logo">✓</span>Check-out</div>',
                    unsafe_allow_html=True)
        secao_anterior = None
        for i, e in enumerate(ETAPAS):
            if e["secao"] != secao_anterior:
                st.markdown(f'<div class="ck-sec">{e["secao"]}</div>', unsafe_allow_html=True)
                secao_anterior = e["secao"]
            rotulo = e["titulo"]
            if e["id"] in COMODO_POR_CHAVE:
                c = COMODO_POR_CHAVE[e["id"]]
                rotulo += f"  ·  {len(conferidos(c))}/{len(itens_do_comodo(c))}"
            st.button(rotulo, key=f"menu_{e['id']}", icon=f":material/{e['icone']}:",
                      type="primary" if i == atual else "tertiary", width="stretch",
                      on_click=ir_para_pelo_menu, args=(i,))


# ======================================================================
# TELAS
# ======================================================================
def checar_duplicado(historico):
    return (not historico.empty
            and {"Data", "Apartamento"}.issubset(historico.columns)
            and ((historico["Data"] == data_str())
                 & (historico["Apartamento"] == apartamento())).any())


def tela_identificacao(etapa, historico):
    with st.container(border=True, key="card-1"):
        titulo_cartao("apartment", "Qual apartamento?",
                      descricao="Escolha o apartamento que está sendo vistoriado.")
        st.segmented_control("Apartamento", APARTAMENTOS, key="w_apartamento",
                             label_visibility="collapsed", width="stretch")
    with st.container(border=True, key="card-2"):
        with st.container(key="lin-ident", horizontal=True):
            st.date_input("Data da vistoria", format="DD/MM/YYYY", key="w_data")
            st.text_input("Responsável pela vistoria", key="w_responsavel",
                          placeholder="Nome de quem está conferindo")
    duplicado = checar_duplicado(historico)
    if duplicado:
        st.warning(f"Já existe um check-out do {apartamento()} em {ss.w_data:%d/%m/%Y}. "
                   "Escolha outra data ou consulte o Histórico.", icon=":material/warning:")
    navegacao(etapa, rotulo_proximo="Começar check-out", desabilitar_proximo=duplicado)


def tela_comodo(etapa):
    c = COMODO_POR_CHAVE[etapa["id"]]
    total, feitos = len(itens_do_comodo(c)), len(conferidos(c))
    with st.container(border=True, key="card-3"):
        titulo_cartao(c["icone"], c["titulo"], f"{feitos} de {total} conferidos",
                      "Toque nos itens que estão conferidos e em bom estado.")
        for grupo, itens in c["grupos"].items():
            rotulo_grupo(grupo)
            with st.container(key=f"grade-{c['chave']}-{slug(grupo)}"):
                for item in itens:
                    st.checkbox(item, key=f"w_{c['chave']}_{item}")
    with st.container(key="lin-extras", horizontal=True):
        tem_obs = bool(ss.get(f"w_{c['chave']}_obs"))
        with st.expander("Observação" + (" ✓" if tem_obs else ""), icon=":material/chat:"):
            st.text_area("Observações", key=f"w_{c['chave']}_obs",
                         placeholder="Ex.: mancha no lado esquerdo do colchão",
                         label_visibility="collapsed")
        bloco_fotos(c["chave"], c["titulo"])
    navegacao(etapa)


def calcular_rouparia():
    """Devolve {item: (deixadas, guardadas, diferença ou None)} e o prejuízo total."""
    linhas, prejuizo, faltando = {}, 0, 0
    for item, info in ESTOQUE_ROUPARIA.items():
        deix, guard = ss.get(f"w_deix_{item}", 0), ss.get(f"w_guard_{item}", 0)
        total = deix + guard
        dif = info["qtd"] - total if total > 0 else None
        if dif and dif > 0:
            prejuizo += dif * info["valor"]
            faltando += dif
        linhas[item] = (deix, guard, dif)
    return linhas, prejuizo, faltando


def tela_rouparia(etapa):
    linhas, prejuizo, faltando = calcular_rouparia()
    with st.container(border=True, key="card-4"):
        titulo_cartao("local_laundry_service", "Rouparia",
                      descricao="Informe quantas peças ficaram em uso e quantas estão guardadas.")
        for item, info in ESTOQUE_ROUPARIA.items():
            dif = linhas[item][2]
            if dif is None:
                status = '<span class="ck-pill">Não contado</span>'
            elif dif == 0:
                status = '<span class="ck-pill ok">OK</span>'
            elif dif > 0:
                status = f'<span class="ck-pill bad">Faltando {dif}</span>'
            else:
                status = f'<span class="ck-pill warn">{abs(dif)} a mais</span>'
            with st.container(key=f"roupa-{slug(item)}"):
                st.markdown(f'<div class="ck-row-head"><span><b>{item}</b>'
                            f'<span class="ck-muted"> · esperado {info["qtd"]}</span></span>'
                            f'{status}</div>', unsafe_allow_html=True)
                with st.container(key=f"lin-roupa-{slug(item)}", horizontal=True):
                    st.number_input("Deixadas", min_value=0, step=1, key=f"w_deix_{item}")
                    st.number_input("Guardadas", min_value=0, step=1, key=f"w_guard_{item}")
    if faltando:
        st.error(f"{faltando} peça(s) faltando · prejuízo estimado de {reais(prejuizo)}",
                 icon=":material/error:")
    else:
        st.success("Nenhuma perda registrada na rouparia", icon=":material/check_circle:")
    navegacao(etapa)


def tela_cozinha(etapa):
    with st.container(border=True, key="card-5"):
        titulo_cartao("kitchen", "Cozinha", descricao="Informe a quantidade de cada item.")
        for grupo, itens in COZINHA.items():
            rotulo_grupo(grupo)
            with st.container(key=f"grade-num-{slug(grupo)}"):
                for item in itens:
                    st.number_input(item, min_value=0, step=1, key=f"w_coz_{item}")
    with st.container(border=True, key="card-6"):
        titulo_cartao("skillet", "Panelas e frigideiras")
        for nome in PANELAS:
            with st.container(key=f"panela-{slug(nome)}"):
                with st.container(key=f"lin-panela-{slug(nome)}", horizontal=True,
                                  vertical_alignment="bottom"):
                    st.number_input(nome, min_value=0, step=1, key=f"w_pan_{nome}_qtd")
                    st.multiselect("Estado", ESTADOS_PANELAS, placeholder="Estado",
                                   key=f"w_pan_{nome}_estado")
    with st.container(key="lin-extras", horizontal=True):
        bloco_fotos("cozinha", "Cozinha")
    navegacao(etapa)


def tela_finalizacao(etapa, historico):
    _, prejuizo, faltando = calcular_rouparia()
    with st.container(border=True, key="card-7"):
        titulo_cartao("task_alt", "Resumo do check-out",
                      f"{apartamento()} · {ss.w_data:%d/%m/%Y}")
        linhas = []
        for c in COMODOS:
            total, feitos = len(itens_do_comodo(c)), len(conferidos(c))
            n_fotos = len(ss.fotos.get(c["chave"], []))
            tem_obs = bool(ss.get(f"w_{c['chave']}_obs"))
            classe = "ok" if feitos == total else "warn"
            extras = []
            if tem_obs:
                extras.append("observação")
            if n_fotos:
                extras.append(f"{n_fotos} foto(s)")
            linhas.append(
                f'<div class="ck-sum-row"><span>{c["titulo"]}</span>'
                f'<span class="ck-muted">{" · ".join(extras)}</span>'
                f'<span class="ck-pill {classe}">{feitos}/{total}</span></div>')
        classe_r = "bad" if faltando else "ok"
        texto_r = f"{faltando} faltando · {reais(prejuizo)}" if faltando else "sem perdas"
        linhas.append(f'<div class="ck-sum-row"><span>Rouparia</span><span></span>'
                      f'<span class="ck-pill {classe_r}">{texto_r}</span></div>')
        n_coz = len(ss.fotos.get("cozinha", []))
        linhas.append(f'<div class="ck-sum-row"><span>Cozinha</span>'
                      f'<span class="ck-muted">{f"{n_coz} foto(s)" if n_coz else ""}</span>'
                      f'<span class="ck-pill">contada</span></div>')
        st.markdown("".join(linhas), unsafe_allow_html=True)
        pendentes = sum(len(itens_do_comodo(c)) - len(conferidos(c)) for c in COMODOS)
        if pendentes:
            st.caption(f"{pendentes} item(ns) não marcados serão registrados como "
                       "não conferidos.")

    with st.container(border=True, key="card-8"):
        titulo_cartao("flag", "Fechamento")
        st.radio("Apartamento liberado?", ["Sim", "Não"], horizontal=True, key="w_liberado")
        st.text_area("Observações finais", key="w_obs_finais",
                     placeholder="Algo que a próxima pessoa precisa saber")

    duplicado = checar_duplicado(historico)
    if duplicado:
        st.warning("Já existe um check-out para este apartamento nesta data.",
                   icon=":material/warning:")
    with st.container(key="nav-rodape", horizontal=True):
        st.button("Voltar", icon=":material/arrow_back:", key="nav_voltar",
                  on_click=ir_para, args=(IDX["final"] - 1,), width="stretch")
        salvar = st.button("Finalizar e salvar", icon=":material/save:", type="primary",
                           key="nav_salvar", disabled=duplicado, width="stretch")
    if salvar:
        try:
            with st.spinner("Enviando fotos e salvando o check-out..."):
                salvar_checkout()
            carregar_historico.clear()
            ss["mensagem_sucesso"] = (f"Check-out de {apartamento()} "
                                      f"({ss.w_data:%d/%m/%Y}) salvo.")
            ss["limpar_formulario"] = True
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Não foi possível salvar: {e}")


def tela_historico(historico):
    if historico.empty:
        with st.container(border=True, key="card-9"):
            st.info("Ainda não existem check-outs salvos.", icon=":material/info:")
        return
    with st.container(border=True, key="card-10"):
        with st.container(key="lin-filtros", horizontal=True):
            datas = sorted(historico["Data"].unique(), reverse=True)
            data_f = st.selectbox("Data", ["Todas"] + datas, key="filtro_data")
            apt_f = st.selectbox("Apartamento",
                                 ["Todos"] + sorted(historico["Apartamento"].unique()),
                                 key="filtro_apto")
        df = historico.copy()
        if data_f != "Todas":
            df = df[df["Data"] == data_f]
        if apt_f != "Todos":
            df = df[df["Apartamento"] == apt_f]
        ordem = [c for c in ["Data", "Registrado em"] if c in df.columns]
        if ordem:
            df = df.sort_values(ordem, ascending=False)
        cols_falt = [c for c in df.columns if "qtd_faltante" in c]
        st.dataframe(df.style.map(colorir_faltante, subset=cols_falt),
                     width="stretch", hide_index=True)

    with st.container(border=True, key="card-11"):
        titulo_cartao("photo_library", "Fotos do check-out")
        opcoes = [f"{r['Data']} – {r['Apartamento']}" for _, r in df.iterrows()]
        escolha = st.selectbox("Check-out", ["Selecione"] + opcoes, key="filtro_fotos",
                               label_visibility="collapsed")
        if escolha == "Selecione":
            return
        linha = df.iloc[opcoes.index(escolha)]
        cols_fotos = [c for c in df.columns if c.startswith("Fotos - ") and linha[c]]
        if not cols_fotos:
            st.caption("Esse check-out não tem fotos.")
            return
        for col in cols_fotos:
            rotulo_grupo(col.replace("Fotos - ", ""))
            imagens = []
            for link in linha[col].split(" | "):
                try:
                    imagens.append(baixar_foto(link.split("/d/")[1].split("/")[0]))
                except Exception as e:  # noqa: BLE001
                    st.warning(f"Não foi possível abrir {link}: {e}")
            if imagens:
                st.image(imagens, width=220)


# ======================================================================
# REGISTRO
# ======================================================================
def montar_registro():
    r = {
        "Data": data_str(),
        "Apartamento": apartamento(),
        "Registrado em": datetime.now(FUSO).strftime("%Y-%m-%d %H:%M:%S"),
        "Responsável": ss.get("w_responsavel", ""),
        "Liberado": ss.get("w_liberado", ""),
        "Obs finais": ss.get("w_obs_finais", ""),
    }
    for c in COMODOS:
        feitos = conferidos(c)
        r[f"{c['titulo']} - Conferidos"] = ", ".join(feitos)
        r[f"{c['titulo']} - Não conferidos"] = ", ".join(
            i for i in itens_do_comodo(c) if i not in feitos)
        r[f"{c['titulo']} - Obs"] = ss.get(f"w_{c['chave']}_obs", "")

    linhas, prejuizo, _ = calcular_rouparia()
    for item, (deix, guard, dif) in linhas.items():
        r[f"Rouparia - {item} - Deixadas"] = deix
        r[f"Rouparia - {item} - Guardadas"] = guard
        r[f"Rouparia - {item} - qtd_faltante"] = "" if dif is None else max(dif, 0)
    r["Rouparia - Prejuízo estimado (R$)"] = prejuizo

    for item in itens_cozinha():
        r[f"Cozinha - {item}"] = ss.get(f"w_coz_{item}", 0)
    for nome in PANELAS:
        r[f"{nome} - Qtd"] = ss.get(f"w_pan_{nome}_qtd", 0)
        r[f"{nome} - Estado"] = ", ".join(ss.get(f"w_pan_{nome}_estado", []))
    return r


def salvar_checkout():
    registro = montar_registro()
    grupos = [(c["titulo"], ss.fotos.get(c["chave"], [])) for c in COMODOS]
    grupos.append(("Cozinha", ss.fotos.get("cozinha", [])))

    nome_checkout = f"{data_str()}_{slug(apartamento())}"
    if any(fotos for _, fotos in grupos):
        drive = conectar_drive()
        pasta_id = obter_ou_criar_pasta(drive, nome_checkout, pasta_raiz_fotos())
        for titulo, fotos in grupos:
            registro[f"Fotos - {titulo}"] = (
                enviar_fotos(drive, fotos, pasta_id, f"{nome_checkout}_{slug(titulo)}")
                if fotos else "")
    salvar_registro(registro)


# ======================================================================
# APP
# ======================================================================
iniciar_estado()
carregar_css()

etapa = ETAPAS[ss.etapa]
menu_lateral(ss.etapa)
fechar_menu_no_celular()
rolar_para_o_topo()
cabecalho(etapa)

if msg := ss.pop("mensagem_sucesso", None):
    st.success(msg, icon=":material/check_circle:")

precisa_historico = etapa["id"] in ("ident", "final", "hist")
historico = pd.DataFrame()
if precisa_historico:
    try:
        historico = carregar_historico()
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível ler o histórico no Google Sheets: {e}",
                 icon=":material/cloud_off:")

if etapa["id"] == "ident":
    tela_identificacao(etapa, historico)
elif etapa["id"] in COMODO_POR_CHAVE:
    tela_comodo(etapa)
elif etapa["id"] == "rouparia":
    tela_rouparia(etapa)
elif etapa["id"] == "cozinha":
    tela_cozinha(etapa)
elif etapa["id"] == "final":
    tela_finalizacao(etapa, historico)
else:
    tela_historico(historico)
