# -*- coding: utf-8 -*-
"""
Ponto de entrada raiz para o monitor em tempo real do Triple Screen B3.
"""
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH se necessário
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.monitor_realtime import MonitorRealtimeB3, CESTA_ACOES

if __name__ == "__main__":
    monitor = MonitorRealtimeB3(CESTA_ACOES)
    monitor.executar_ciclo()

