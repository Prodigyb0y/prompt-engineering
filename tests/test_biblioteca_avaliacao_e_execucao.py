import json

import pytest

import avaliadores as av
import cliente as c
import experimentos as ex
import prompts_biblioteca as pb
from custo import carregar_precos

PRECOS = carregar_precos()


# ------------------------------------------------------------------ P2
def test_p2_acerta_so_com_as_duas_chaves_certas():
    g = {"categoria": "rede", "urgencia": "alta"}
    assert av.avaliar_p2('{"categoria": "rede", "urgencia": "alta"}', g)["caso_correto"]
    assert av.avaliar_p2('```json\n{"categoria": "rede", "urgencia": "alta"}\n```', g)["caso_correto"]   # cerca de markdown tolerada
    assert not av.avaliar_p2('{"categoria": "rede", "urgencia": "media"}', g)["caso_correto"]
    assert not av.avaliar_p2('{"categoria": "rede", "urgencia": "alta", "extra": 1}', g)["caso_correto"]
    assert not av.avaliar_p2("rede, alta", g)["json_valido"]
    r = av.avaliar_p2('{"categoria": "acesso", "urgencia": "alta"}', g)
    assert r["campos"] == {"categoria": False, "urgencia": True}


# ------------------------------------------------------------------ P3
EMAIL = "Assunto: Informações para o seu pedido\n\nOlá! Recebi seu pedido de 10 caixas de papel A4. Para seguir, preciso do {x}. Obrigado!\n\nEquipe de Compras · Gutenberg Systems"


def test_p3_exige_exatamente_os_campos_que_faltam():
    g = {"faltantes": ["prazo_entrega", "fornecedor"]}
    ok = av.avaliar_p3(EMAIL.format(x="Prazo de ENTREGA e o fornecedor"), g)
    assert ok["caso_correto"] and ok["citados"] == ["fornecedor", "prazo_entrega"] and ok["formato_ok"]
    assert av.avaliar_p3(EMAIL.format(x="prazo de entrega"), g)["faltou_citar"] == ["fornecedor"]
    a_mais = av.avaliar_p3(EMAIL.format(x="prazo de entrega, fornecedor e valor unitário"), g)
    assert not a_mais["caso_correto"] and a_mais["citou_a_mais"] == ["valor_unitario"]
    assert av.avaliar_p3(EMAIL.format(x="prazo de entrega e fornecedor (sem acento: valor unitario)"), g)["citou_a_mais"] == ["valor_unitario"]


def test_p3_sem_faltantes_so_vale_a_sentinela():
    g = {"faltantes": []}
    assert av.avaliar_p3(" NENHUM_CAMPO_FALTANTE \n", g)["caso_correto"]
    assert not av.avaliar_p3(EMAIL.format(x="nada"), g)["caso_correto"]
    assert not av.avaliar_p3(pb.P3_SENTINELA, {"faltantes": ["fornecedor"]})["caso_correto"]


def test_p3_formato_e_informacao_a_parte_nao_entra_no_acerto():
    longo = "Assunto: x\n\n" + "palavra " * 130 + "fornecedor"
    r = av.avaliar_p3(longo, {"faltantes": ["fornecedor"]})
    assert r["caso_correto"] and not r["formato_ok"] and r["palavras_corpo"] > av.MAX_PALAVRAS_EMAIL


# ------------------------------------------------------------------ P4
TEXTO4 = "O monitor do pedido PED-32561 chegou com defeito. Paguei R$ 1.899,90."
G4 = {"motivo": "produto_com_defeito", "sentimento": "insatisfeito", "acao_sugerida": "trocar_produto",
      "numero_pedido": "PED-32561", "valor_reclamado": 1899.9}


def resp4(**mud):
    base = {"resumo": "Monitor do pedido PED-32561 chegou com defeito.", "motivo": "produto_com_defeito", "sentimento": "insatisfeito",
            "acao_sugerida": "trocar_produto", "numero_pedido": "PED-32561", "valor_reclamado": 1899.9}
    base.update(mud)
    return json.dumps(base, ensure_ascii=False)


def test_p4_acerta_quando_tudo_bate():
    assert av.avaliar_p4(resp4(), G4, TEXTO4)["caso_correto"]


def test_p4_detecta_invencao_de_numero_e_valor():
    g = {**G4, "numero_pedido": None, "valor_reclamado": None}
    r = av.avaliar_p4(resp4(), g, "O monitor chegou com defeito.")
    assert not r["caso_correto"] and r["invencoes"] == 2 and not r["campos"]["resumo"]   # PED-32561 no resumo, que não está no texto
    ok = av.avaliar_p4(resp4(numero_pedido=None, valor_reclamado=None, resumo="Monitor chegou com defeito."), g, "O monitor chegou com defeito.")
    assert ok["caso_correto"] and ok["invencoes"] == 0


def test_p4_regras_de_tipo_e_tamanho():
    assert not av.avaliar_p4(resp4(valor_reclamado="1899,90"), G4, TEXTO4)["caso_correto"]       # string não vale
    assert not av.avaliar_p4(resp4(resumo=" ".join(["a"] * 21)), G4, TEXTO4)["campos"]["resumo"]
    assert not av.avaliar_p4(resp4(motivo="defeito"), G4, TEXTO4)["caso_correto"]
    assert not av.avaliar_p4(json.dumps({"motivo": "x"}), G4, TEXTO4)["caso_correto"]


# ------------------------------------------------------------------ P5
def test_p5_le_so_o_bloco_json_no_chain_of_thought():
    g = {"decisao": "escalar"}
    cot = '<raciocinio>Total 5250, acima. Poderia aprovar? Não. "decisao": "aprovar" seria erro.</raciocinio>\n<json>{"decisao": "escalar", "motivo": "acima do limite"}</json>'
    assert av.avaliar_p5(cot, g, cot=True)["caso_correto"]
    assert not av.avaliar_p5(cot, g, cot=False)["json_valido"]            # sem a tag, o texto todo não é JSON
    assert not av.avaliar_p5('{"decisao": "aprovar", "motivo": "ok"}', g)["caso_correto"]
    assert not av.avaliar_p5('{"decisao": "escalar"}', g)["caso_correto"]  # falta a chave motivo
    assert not av.avaliar_p5("<raciocinio>sem json</raciocinio>", g, cot=True)["json_valido"]


# ------------------------------------------------------------------ executor com cliente falso
def _gab():
    return {n: ex.carregar_dados(n)[1] for n in ("p2", "p3", "p4", "p5")}


class Falso:
    """Responde o que o gabarito pede, a partir do prompt recebido. Conta chamadas."""

    def __init__(self, erro_em=None):
        self.n, self.erro_em, self.gab = 0, erro_em, _gab()
        self.casos = {nome: {cc["texto"]: cc["id"] for cc in ex.carregar_dados(nome)[0]} for nome in self.gab}

    def __call__(self, system, user, max_tokens):
        self.n += 1
        if self.erro_em and self.n == self.erro_em:
            raise ValueError("falha permanente")
        txt = {"texto": "", "tokens_entrada": 1000, "tokens_saida": 100}
        if "Categorias (escolha uma)" in user:
            cid = self._achar("p2", user)
            txt["texto"] = json.dumps(self.gab["p2"][cid])
        elif user.startswith("Dados extraídos (JSON):"):
            dados = json.loads(user.split("\n", 1)[1])
            falta = [r for k, r in pb.P3_CAMPOS if dados.get(k) is None]
            txt["texto"] = (pb.P3_SENTINELA if not falta else "Assunto: Dados\n\nPreciso de: " + ", ".join(falta) + ". Obrigado!")
        elif user.startswith("Mensagem da solicitação:"):
            cid = self._achar("p3", user)
            falta = [r for k, r in pb.P3_CAMPOS if k in self.gab["p3"][cid]["faltantes"]]
            txt["texto"] = (pb.P3_SENTINELA if not falta else "Assunto: Dados\n\nPreciso de: " + ", ".join(falta) + ". Obrigado!")
        elif user.startswith("Solicitação:\n") and "Gutenberg Systems, empresa fictícia.\nSua única tarefa" in system:   # P1 (T4 v2)
            cid = self._achar("p3", user)
            txt["texto"] = json.dumps(self.gab["p3"][cid]["extracao"], ensure_ascii=False)
        elif user.startswith("Reclamação:"):
            cid = self._achar("p4", user)
            g = self.gab["p4"][cid]
            txt["texto"] = json.dumps({"resumo": "Cliente reclama.", **g}, ensure_ascii=False)
        elif user.startswith("Solicitação (JSON):"):
            cid = self._achar("p5", user)
            j = json.dumps({"decisao": self.gab["p5"][cid]["decisao"], "motivo": "pela política"})
            txt["texto"] = f"<raciocinio>passos</raciocinio><json>{j}</json>" if "<raciocinio>" in system else j
        else:
            raise AssertionError("prompt inesperado")
        return txt

    def _achar(self, nome, user):
        return next(i for t, i in self.casos[nome].items() if t in user)


def cliente_falso(tmp_path, falso=None, teto=ex.TETO_RODADAS_USD, anterior=ex.GASTO_ANTERIOR_USD):
    ctl = ex.ControleBiblioteca(tmp_path / "gasto.json", teto=teto, anterior=anterior)
    return c.ClienteAnthropic(ctl, PRECOS, enviar=falso or Falso(), dormir=lambda s: None), ctl


def test_rodada_completa_com_respostas_certas_da_100_por_cento_e_grava_tudo(tmp_path):
    cli, _ = cliente_falso(tmp_path)
    for exp, var in ex.ORDEM:
        feitas, novas, parou = ex.executar_variante(cli, exp, var, pasta=tmp_path / "brutos")
        assert (feitas, novas, parou) == (0, 60, None), (exp, var)
        linhas = [json.loads(x) for x in (tmp_path / "brutos" / f"{exp}_{var}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(linhas) == 60 and all(l["avaliacao"]["caso_correto"] for l in linhas), (exp, var)
        assert {l["repeticao"] for l in linhas} == {1, 2, 3} and all(l["modelo"] == "claude-haiku-5-5" and l["esforco"] == "low" for l in linhas)


def test_fluxo_encadeado_usa_duas_chamadas_e_soma_custo(tmp_path):
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    ex.executar_variante(cli, "E4", "encadeado", pasta=tmp_path / "b", limite_casos=2, reps=1)
    assert falso.n == 4          # 2 casos x (P1 + P3)
    reg = json.loads((tmp_path / "b" / "E4_encadeado.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [e["prompt"] for e in reg["etapas"]] == ["P1", "P3"]
    assert reg["custo_usd"] == pytest.approx(sum(e["custo_usd"] for e in reg["etapas"]))
    # a entrada do P3 é a resposta do P1, não o gabarito
    assert reg["etapas"][1]["hash12"] == pb.carregar("P3", "encadeado")["hash12"]


def test_unico_usa_uma_chamada_por_caso(tmp_path):
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    ex.executar_variante(cli, "E4", "unico", pasta=tmp_path / "b", limite_casos=2, reps=1)
    assert falso.n == 2


def test_execucao_e_retomavel(tmp_path):
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    ex.executar_variante(cli, "E3", "few_shot", pasta=tmp_path / "b", limite_casos=3)
    n1 = falso.n
    feitas, novas, parou = ex.executar_variante(cli, "E3", "few_shot", pasta=tmp_path / "b", limite_casos=3)
    assert (feitas, novas, parou) == (9, 0, None) and falso.n == n1


def test_para_no_primeiro_erro_e_nao_repete_em_laco(tmp_path):
    falso = Falso(erro_em=4)
    cli, _ = cliente_falso(tmp_path, falso)
    feitas, novas, parou = ex.executar_variante(cli, "E3", "zero_shot", pasta=tmp_path / "b")
    assert novas == 3 and parou.startswith("ValueError") and falso.n == 4
    assert (tmp_path / "gasto.json").exists()


def test_teto_das_rodadas_novas_bloqueia_antes_de_chamar(tmp_path):
    falso = Falso()
    cli, ctl = cliente_falso(tmp_path, falso, teto=0.0030)
    feitas, novas, parou = ex.executar_variante(cli, "E3", "few_shot", pasta=tmp_path / "b")
    assert parou.startswith("TetoExcedido") and novas >= 1
    assert ctl.gasto <= 0.0030 and falso.n == novas            # a chamada bloqueada nunca saiu
    assert "teto excedido" in (tmp_path / "erros.log").read_text(encoding="utf-8")


def test_total_do_repositorio_nunca_passa_de_um_dolar(tmp_path):
    falso = Falso()
    cli, ctl = cliente_falso(tmp_path, falso, anterior=0.999)       # sobra US$ 0,001 do teto total; teto das rodadas novas seria 0,60
    feitas, novas, parou = ex.executar_variante(cli, "E5", "cot", pasta=tmp_path / "b")
    assert parou.startswith("TetoExcedido") and ctl.anterior + ctl.gasto <= 1.0 and falso.n == novas
    assert "teto total excedido" in (tmp_path / "erros.log").read_text(encoding="utf-8")


def test_piloto_faz_5_chamadas_por_prompt_novo_e_projeta_custo(tmp_path):
    falso = Falso()
    cli, _ = cliente_falso(tmp_path, falso)
    r = ex.executar_piloto(cli, pasta=tmp_path / "piloto")
    assert falso.n == 20 and [r[k]["chamadas"] for k in ("P2", "P3", "P4", "P5")] == [5, 5, 5, 5]
    assert r["projecao_rodada_completa_usd"] == pytest.approx(ex.projetar(r)) and 0 < r["projecao_rodada_completa_usd"] < ex.TETO_RODADAS_USD
    assert (tmp_path / "piloto" / "piloto.json").exists()


def test_projecao_da_rodada_completa_cabe_no_teto_com_custo_tipico():
    # custo por chamada generoso (3x o do T4 medido) ainda cabe nos US$ 0,60
    piloto = {k: {"custo_medio_usd": 0.0005} for k in ("P2", "P3", "P4", "P5")}
    assert ex.projetar(piloto) < ex.TETO_RODADAS_USD
    # 480 chamadas no total: E3 120 + E4 (120 do fluxo + 60 do único) + P4 60 + E5 120, a 3 repetições
    assert ex.projetar({k: {"custo_medio_usd": 1.0} for k in ("P2", "P3", "P4", "P5")}) == pytest.approx(60 * 2 + 60 * (1 + ex.CUSTO_P1_ESTIMADO) + 60 + 60 + 120)
