# App de Check-out – Verificação dos Apartamentos (Airbnb)
![APP Checkout](https://github.com/Raquelrs3/datasus/assets/98356094/86267024-544c-46b8-9dde-1779fffd34e1)


Este é um projeto de gestão dos meus próprios apartamentos anunciados no Airbnb. É uma aplicação web em Streamlit, usada no celular durante a vistoria de saída do hóspede.


## 1. Problema de Negócio
Depois de cada hospedagem, o apartamento precisa ser conferido antes de ser liberado para o próximo hóspede: móveis, eletrônicos, enxoval, utensílios de cozinha e o estado geral de cada cômodo. Sem um padrão de vistoria e sem registro, fica difícil saber o que foi conferido, comprovar danos com fotos e calcular perdas de rouparia e utensílios.


## 2. Entendimento do Negócio
#### Motivação
Padronizar a vistoria de check-out e ter um histórico consultável de cada saída de hóspede, com evidências (fotos) e o prejuízo estimado quando falta algum item.

#### Causa Raiz do Problema
Conferência feita sem roteiro fixo e sem registro centralizado: itens esquecidos, nenhuma foto do estado do apartamento na data e nenhum controle do enxoval por hospedagem.

#### Quem é o Stakeholder
A gestora dos apartamentos e quem faz a vistoria (limpeza ou auxiliar).

#### Formato da Solução
* Aplicação web acessada pelo link, no celular ou no computador,
* Checklist por ambiente, com observações e fotos,
* Contagem de rouparia com prejuízo estimado em R$, e contagem de itens da cozinha,
* Registro salvo no Google Sheets e fotos organizadas no Google Drive,
* Histórico de check-outs com filtro e visualização das fotos.


## 3. Metodologia de Desenvolvimento do Projeto
O projeto foi desenvolvido em ciclos curtos (MVP → validação → melhoria):
* Versão funcional de ponta a ponta já na primeira entrega,
* Testes no Google Colab antes de cada publicação,
* Ajustes de design a partir do uso real no celular.


##### Passo 01 - Levantamento do inventário: Lista de itens de cada ambiente (quartos, sala, banheiros, lavabo), estoque de rouparia com o valor de reposição de cada peça e itens da cozinha.


##### Passo 02 - Protótipo em Streamlit: Primeira versão em página única, com checklist, observações e upload de fotos.


##### Passo 03 - Integração com o Google: Registro de cada check-out no Google Sheets (conta de serviço) e envio das fotos ao Google Drive (OAuth da conta da gestora), com uma subpasta por check-out.


##### Passo 04 - Regras de negócio: Bloqueio de check-out duplicado (mesmo apartamento e data), cálculo de peças faltando e do prejuízo estimado da rouparia, e redução automática das fotos para agilizar o envio pelo celular.


##### Passo 05 - Redesenho da interface: Fluxo em etapas (uma tela por ambiente), menu lateral com o progresso de cada cômodo, itens em cartões clicáveis e tema cinza, vermelho e branco, pensado primeiro para o celular.


##### Passo 06 - Deploy: Código no GitHub e publicação no Streamlit Community Cloud, com as credenciais guardadas nos Secrets da plataforma.


## 4. Entendendo os Dados
Cada check-out gera **uma linha** na aba `checkouts` da planilha. As colunas são criadas automaticamente no primeiro salvamento.

| VARIÁVEL  |  DEFINIÇÃO  |
| ------------------- | ------------------- |
| Data | Data da vistoria (AAAA-MM-DD) |
| Apartamento | Apartamento vistoriado |
| Registrado em | Data e hora do salvamento (horário de Brasília) |
| Responsável | Quem fez a vistoria |
| Liberado | Se o apartamento foi liberado para o próximo hóspede (Sim/Não) |
| Obs finais | Observações gerais do check-out |
| [Cômodo] - Conferidos | Itens marcados como conferidos e em bom estado |
| [Cômodo] - Não conferidos | Itens que não foram marcados |
| [Cômodo] - Obs | Observação do cômodo |
| Rouparia - [Item] - Deixadas / Guardadas | Peças em uso e peças guardadas |
| Rouparia - [Item] - qtd_faltante | Peças faltando em relação ao estoque esperado |
| Rouparia - Prejuízo estimado (R$) | Soma do valor de reposição das peças faltando |
| Cozinha - [Item] | Quantidade contada de cada utensílio |
| [Panela] - Qtd / Estado | Quantidade e estado de conservação de cada panela |
| Fotos - [Cômodo] | Links das fotos no Google Drive |

**Regra de nome das fotos no Drive:**
```
<pasta raiz>/2026-10-24_Citta_Residence/2026-10-24_Citta_Residence_Quarto_1_01.jpg
```
Data do check-out + apartamento + cômodo + número da foto, o que permite identificar cada foto sem abrir a planilha.


## 5. Principais Funcionalidades

**Identificação**
Escolha do apartamento, data e responsável. O app avisa logo no início se já existe um check-out daquele apartamento na data.

![tela_identificacao](docs/prints/identificacao.png)


**Checklist por ambiente**
Uma tela por cômodo, itens agrupados (móveis, eletrônicos, estrutura...) e contador de itens conferidos. Observação e fotos abrem só quando necessário.

![tela_comodo](docs/prints/comodo.png)


**Rouparia e cozinha**
Contagem das peças deixadas e guardadas, com o status de cada item (OK, faltando, a mais) e o prejuízo estimado.

![tela_rouparia](docs/prints/rouparia.png)


**Finalização e histórico**
Resumo de todo o check-out antes de salvar e histórico com filtros por data e apartamento, incluindo as fotos.

![tela_finalizacao](docs/prints/finalizacao.png)


## 6. Arquitetura e Tecnologias

| CAMADA | TECNOLOGIA |
| ------------------- | ------------------- |
| Interface | Python + Streamlit (CSS próprio e tema em `.streamlit/config.toml`) |
| Registro dos check-outs | Google Sheets (gspread + conta de serviço) |
| Fotos | Google Drive API (OAuth) + Pillow para reduzir as imagens |
| Código | GitHub |
| Hospedagem | Streamlit Community Cloud |
| Testes | Google Colab + ngrok |

**Estrutura do repositório**
```
├── app.py                  # aplicação
├── design.css              # acabamento visual
├── requirements.txt        # bibliotecas
├── .streamlit/config.toml  # tema (cinza, vermelho e branco)
└── docs/prints/            # imagens deste README
```
As credenciais (`secrets.toml` e arquivos `.json`) **não** ficam no repositório: elas são configuradas nos Secrets do Streamlit Cloud.


## 7. Resultado Final
A vistoria de check-out passou a seguir um roteiro único, feito pelo celular, com o registro salvo automaticamente e as fotos organizadas por data e apartamento. O histórico permite consultar qualquer saída de hóspede e o prejuízo da rouparia de cada uma.


## - Conclusão

O app resolve a etapa de saída do hóspede dentro do projeto de gestão do Airbnb. Os registros na planilha também podem alimentar as análises do projeto, como perdas de enxoval ao longo do tempo e itens que mais se danificam.

**Próximos passos**
* Salvar um rascunho a cada cômodo concluído, para não perder a vistoria se a conexão cair,
* Levar os registros de check-out para o Databricks como mais uma fonte da camada bronze.


**Como usar o app:**
**Acesse o link pelo celular, escolha o apartamento e a data, siga as etapas com os botões Voltar e Próximo e finalize na tela de resumo. [Clique aqui](LINK_DO_APP) para acessar.**
