with open('src/black_scholes_engine.py', 'r') as f:
    content = f.read()

idx = content.find('    def gerar_grade_5_strikes(')

new_func = """    def gerar_grade_5_strikes(
        self,
        ticker: str,
        spot: float,
        sigma: float,
        tipo: str = "CALL",
        passo_strike: float = 1.0,
        data_base: Optional[date] = None
    ) -> Tuple[pd.DataFrame, date, int]:
        \"\"\"
        Gera a grade oficial de 5 strikes (-6% ITM, -3% ITM, ATM, +3% OTM, +6% OTM)
        com strikes arredondados pela grade B3 e prêmios/gregas recalculados via Black-Scholes.
        \"\"\"
        vencimento, dias_uteis = obter_vencimento_mensal_alvo(data_base)
        mes_venc = vencimento.month
        raiz = ticker.replace(".SA", "")[:4]
        tabela = LETRAS_CALL if tipo.upper() == "CALL" else LETRAS_PUT
        letra = tabela.get(mes_venc, 'K' if tipo.upper() == "CALL" else 'W')

        if tipo.upper() == "CALL":
            degraus = [(-0.06, "ITM (Dentro)"), (-0.03, "ITM (Dentro)"), (0.00,  "ATM (No Dinheiro)"), (0.03,  "OTM (Fora)"), (0.06,  "OTM (Fora)")]
        else:
            degraus = [(0.06,  "ITM (Dentro)"), (0.03,  "ITM (Dentro)"), (0.00,  "ATM (No Dinheiro)"), (-0.03, "OTM (Fora)"), (-0.06, "OTM (Fora)")]

        strikes_iniciais = [strike_oficial_b3(spot * (1.0 + off), passo=passo_strike) for off, _ in degraus]

        if len(set(strikes_iniciais)) < len(strikes_iniciais):
            atm_s = strike_oficial_b3(spot, passo=passo_strike)
            if tipo.upper() == "CALL":
                strikes_finais = [atm_s - 2*passo_strike, atm_s - passo_strike, atm_s, atm_s + passo_strike, atm_s + 2*passo_strike]
            else:
                strikes_finais = [atm_s + 2*passo_strike, atm_s + passo_strike, atm_s, atm_s - passo_strike, atm_s - 2*passo_strike]
        else:
            strikes_finais = strikes_iniciais

        grade = []
        for strike, (offset, moneyness_label) in zip(strikes_finais, degraus):
            distancia = ((strike - spot) / spot) * 100.0
            
            if strike.is_integer():
                codigo_opcao = f"{raiz}{letra}{int(strike)}"
            else:
                codigo_opcao = f"{raiz}{letra}{str(strike).replace('.', ',')}"

            greeks = self.evaluate_option(spot=spot, strike=strike, dte_business_days=dias_uteis, option_type=tipo, sigma=sigma)
            premio_estimado = round(greeks["theoretical_price"], 2)
            alvo_150 = round(premio_estimado * 2.5, 2)
            delta = round(greeks["delta"], 2)
            gamma = round(greeks["gamma"], 4)
            theta_diario = round(greeks["theta_daily"], 4)

            grade.append({
                "Destaque": "",
                "Código B3": codigo_opcao,
                "Tipo": tipo.upper(),
                "Strike": strike,
                "Distância (%)": round(distancia, 1),
                "Moneyness": moneyness_label,
                "Delta": delta,
                "Gamma": gamma,
                "Theta": theta_diario,
                "Prêmio Est.": premio_estimado,
                "Alvo (+150%)": alvo_150,
                "Vencimento": vencimento.strftime("%d/%m/%Y"),
                "DTE (Dias Úteis)": dias_uteis
            })

        idx_recomendado, menor_distancia = -1, 999.0
        for i, item in enumerate(grade):
            abs_delta = abs(item["Delta"])
            if 0.30 <= abs_delta <= 0.45:
                dist = abs(abs_delta - 0.375)
                if dist < menor_distancia: menor_distancia, idx_recomendado = dist, i
        
        if idx_recomendado == -1:
            for i, item in enumerate(grade):
                dist = abs(abs(item["Delta"]) - 0.375)
                if dist < menor_distancia: menor_distancia, idx_recomendado = dist, i
                    
        if idx_recomendado != -1: grade[idx_recomendado]["Destaque"] = "⭐ RECOMENDADA"

        return pd.DataFrame(grade), vencimento, dias_uteis
"""

if idx != -1:
    content = content[:idx] + new_func
    with open('src/black_scholes_engine.py', 'w') as f:
        f.write(content)
