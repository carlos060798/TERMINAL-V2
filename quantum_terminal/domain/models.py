"""
Domain Models for Quantum Investment Terminal.

Este módulo contiene los modelos principales del dominio para el terminal de inversiones.
Define las entidades fundamentales que representen valores, empresas y datos financieros.

This module contains the main domain models for the investment terminal.
Defines fundamental entities representing stocks, companies and financial data.

Phase 1 - Core Domain Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 1: Domain Architecture
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# TODO: Implementar SecurityData con campos para ticker, nombre, precio actual
# TODO: Implement SecurityData class with ticker, name, current_price fields
@dataclass
class SecurityData:
    """
    Representa los datos básicos de un valor financiero.
    Represents basic financial security data.
    """
    ticker: str
    name: str
    current_price: Decimal
    currency: str = "USD"
    exchange: str = "NYSE"
    last_updated: datetime = None

    def __post_init__(self):
        # TODO: Validar ticker format
        # TODO: Validate ticker format (uppercase, 1-5 chars)
        if self.last_updated is None:
            self.last_updated = datetime.now()


# TODO: Implementar CompanyFundamentals con EBITDA, PE ratio, deuda, etc.
# TODO: Implement CompanyFundamentals with EBITDA, PE ratio, debt metrics
@dataclass
class CompanyFundamentals:
    """
    Datos fundamentales de la empresa para análisis Graham-Dodd.
    Company fundamental data for Graham-Dodd analysis.
    """
    ticker: str
    market_cap: Decimal
    revenue: Decimal
    earnings: Decimal
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None

    # TODO: Agregar métodos de validación
    # TODO: Add validation methods


# TODO: Implementar FinancialStatement (Balance Sheet, Income Statement)
# TODO: Implement FinancialStatement class
@dataclass
class FinancialStatement:
    """
    Estado financiero de una empresa (balance, ingresos, flujos).
    Company financial statement (balance sheet, income, cash flows).
    """
    ticker: str
    period: str  # "Q1 2024", "FY 2023"
    statement_type: str  # "balance_sheet", "income_statement", "cash_flow"
    data: dict
    filing_date: datetime
    currency: str = "USD"

    # TODO: Validar estructura de datos según statement_type
    # TODO: Validate data structure based on statement_type


# TODO: Implementar TimeSeries para precios históricos y métricas
# TODO: Implement TimeSeries for historical prices and metrics
@dataclass
class TimeSeries:
    """
    Serie temporal de datos financieros (precios, métricas).
    Time series of financial data (prices, metrics).
    """
    ticker: str
    metric_name: str
    values: List[dict]  # [{"date": datetime, "value": Decimal}, ...]
    frequency: str = "daily"  # "daily", "weekly", "monthly"

    # TODO: Métodos para cálculo de tendencias
    # TODO: Add trend calculation methods


# TODO: Implementar AnalysisResult para almacenar resultados de análisis
# TODO: Implement AnalysisResult for storing analysis outputs
@dataclass
class AnalysisResult:
    """
    Resultado de un análisis realizado sobre un valor.
    Result of analysis performed on a security.
    """
    ticker: str
    analysis_type: str  # "valuation", "risk", "thesis_score"
    result: dict
    score: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# TODO: Implementar Portfolio para gestión de cartera
# TODO: Implement Portfolio for portfolio management
@dataclass
class Portfolio:
    """
    Cartera de inversiones con posiciones y métricas.
    Investment portfolio with positions and metrics.
    """
    portfolio_id: str
    name: str
    positions: List[dict]  # [{"ticker": str, "shares": Decimal, "cost_basis": Decimal}, ...]
    total_value: Decimal = Decimal(0)
    cash_balance: Decimal = Decimal(0)
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    # TODO: Métodos de cálculo de métricas de cartera
    # TODO: Add portfolio metrics calculation methods
