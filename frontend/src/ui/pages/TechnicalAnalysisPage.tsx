import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../lib/api.ts';
import { LayoutList, LayoutGrid, TrendingUp, TrendingDown, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';

// Complete types
interface TechnicalIndicators {
  rsi: number;
  macd: {
    value: number;
    signal: number;
    histogram: number;
  };
  moving_averages: {
    sma_20: number;
    sma_50: number;
    sma_200: number;
  };
  bollinger_bands: {
    upper: number;
    middle: number;
    lower: number;
  };
  volume: {
    trend: string;
    average: number;
  };
}

interface TechnicalAnalysis {
  asset_id: number;
  symbol: string;
  name: string;
  portfolio_name: string;
  current_price: number;
  purchase_price: number;
  quantity: number;
  invested_value: number;
  current_value: number;
  gain_loss: number;
  gain_loss_percentage: number;
  indicators: TechnicalIndicators;
  recommendation: string;
  action_text: string;
  signals: string[];
  bullish_factors: number;
  bearish_factors: number;
}

// Helper functions
const getRecommendationColor = (recommendation: string): string => {
  switch (recommendation) {
    case 'strong_bullish': return 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950/20 dark:border-green-800';
    case 'bullish': return 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950/20 dark:border-green-800';
    case 'neutral': return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-950/20 dark:border-yellow-800';
    case 'bearish': return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/20 dark:border-red-800';
    case 'strong_bearish': return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/20 dark:border-red-800';
    default: return 'text-muted bg-border/20 border-border';
  }
};

const getRecommendationIcon = (recommendation: string) => {
  switch (recommendation) {
    case 'strong_bullish':
    case 'bullish':
      return <ArrowUpRight className="w-4 h-4" />;
    case 'bearish':
    case 'strong_bearish':
      return <ArrowDownRight className="w-4 h-4" />;
    default:
      return <Activity className="w-4 h-4" />;
  }
};

// RSI Indicator Component
const RSIIndicator = ({ value }: { value: number }) => {
  const getColor = () => {
    if (value < 30) return 'bg-green-500';
    if (value > 70) return 'bg-red-500';
    return 'bg-yellow-500';
  };

  const getLabel = () => {
    if (value < 30) return 'Oversold';
    if (value > 70) return 'Overbought';
    return 'Neutral';
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted">RSI: {value.toFixed(1)}</span>
        <span className={`font-medium ${value < 30 ? 'text-green-600' : value > 70 ? 'text-red-600' : 'text-yellow-600'
          }`}>
          {getLabel()}
        </span>
      </div>
      <div className="h-2 bg-border rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all duration-300`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
};

export default function TechnicalAnalysisPage() {
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');

  const { data: analyses, isLoading } = useQuery({
    queryKey: ['technical-analysis'],
    queryFn: async () => {
      const response = await api.get('/analysis/analysis');
      return response.data as TechnicalAnalysis[];
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted">Loading technical analysis...</div>
      </div>
    );
  }

  if (!analyses || analyses.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted">No holdings found for analysis</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 via-purple-300 to-indigo-500 bg-clip-text text-transparent">
            Technical Analysis & AI Technical Signals
          </h1>
          <p className="text-muted mt-1">
            Technical indicators and market analysis for educational purposes
          </p>
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg dark:bg-amber-950/20 dark:border-amber-800">
            <div className="flex items-start gap-3">
              <div className="text-amber-600 dark:text-amber-400 mt-0.5">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="text-sm text-amber-800 dark:text-amber-200">
                <p className="font-medium mb-2">Important Disclaimer</p>
                <p className="mb-2">
                  This analysis is for educational purposes only and does not constitute investment advice or recommendations.
                  The signals shown (buy/sell/hold) are based on technical indicators and should not be considered as personalized
                  investment recommendations.
                </p>
                <p className="mb-2">
                  <strong>To avoid regulatory requirements:</strong> These are presented as indicator summaries (bullish/bearish signals)
                  rather than actionable advice. No performance claims are made, and this is purely educational content showing
                  how technical indicators work.
                </p>
                <p>
                  Always consult with a SEBI-registered investment advisor for personalized investment decisions.
                  Past performance does not guarantee future results.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* View Toggle Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('table')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${viewMode === 'table'
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md'
              : 'bg-surface text-text hover:bg-surface/80 border border-border'
              }`}
          >
            <LayoutList className="w-4 h-4" />
            Table View
          </button>
          <button
            onClick={() => setViewMode('cards')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${viewMode === 'cards'
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md'
              : 'bg-surface text-text hover:bg-surface/80 border border-border'
              }`}
          >
            <LayoutGrid className="w-4 h-4" />
            Cards View
          </button>
        </div>
      </div>

      {/* Conditional View Rendering */}
      {viewMode === 'table' ? (
        /* Table View */
        <div className="bg-surface rounded-xl shadow-sm border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gradient-to-r from-indigo-50/50 to-purple-50/50 dark:from-indigo-950/30 dark:to-purple-950/30 border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-text uppercase tracking-wider">
                    Asset
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase tracking-wider">
                    Price
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-text uppercase tracking-wider">
                    RSI
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-text uppercase tracking-wider">
                    MACD
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-text uppercase tracking-wider">
                    AI Technical Signals
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analyses.map((analysis) => (
                  <tr key={analysis.asset_id} className="hover:bg-surface/80 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-text">{analysis.symbol}</div>
                        <div className="text-sm text-muted">{analysis.name}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="font-medium text-text">
                        ₹{(analysis.current_price ?? 0).toFixed(2)}
                      </div>
                      <div className="text-sm text-muted">
                        Qty: {analysis.quantity ?? 0}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className={`font-semibold ${(analysis.gain_loss ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                        {(analysis.gain_loss ?? 0) >= 0 ? '+' : ''}₹{(analysis.gain_loss ?? 0).toFixed(2)}
                      </div>
                      <div className={`text-sm ${(analysis.gain_loss_percentage ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                        {(analysis.gain_loss_percentage ?? 0) >= 0 ? '+' : ''}{(analysis.gain_loss_percentage ?? 0).toFixed(2)}%
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="w-40">
                        <RSIIndicator value={analysis.indicators?.rsi ?? 50} />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className={`font-medium ${(analysis.indicators?.macd?.histogram ?? 0) > 0
                        ? 'text-green-600'
                        : 'text-red-600'
                        }`}>
                        {(analysis.indicators?.macd?.value ?? 0).toFixed(2)}
                      </div>
                      <div className="text-xs text-muted">
                        Signal: {(analysis.indicators?.macd?.signal ?? 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col items-center gap-1">
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${getRecommendationColor(analysis.recommendation ?? 'hold')
                          }`}>
                          {getRecommendationIcon(analysis.recommendation ?? 'hold')}
                          {(analysis.recommendation ?? 'hold').replace('_', ' ').toUpperCase()}
                        </span>
                        <span className="text-xs text-muted">
                          Signal Strength
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {analyses.map((analysis) => (
            <div
              key={analysis.asset_id}
              className="bg-surface rounded-xl shadow-sm border border-border overflow-hidden hover:shadow-md transition-shadow"
            >
              {/* Asset Header */}
              <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 text-white">
                <h3 className="text-xl font-bold">{analysis.symbol}</h3>
                <p className="text-indigo-100 text-sm">{analysis.name}</p>
              </div>

              <div className="p-6 space-y-4">
                {/* Price & P&L */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-muted mb-1">Current Price</div>
                    <div className="text-lg font-bold text-text">
                      ₹{(analysis.current_price ?? 0).toFixed(2)}
                    </div>
                    <div className="text-xs text-muted">Qty: {analysis.quantity ?? 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-1">P&L</div>
                    <div className={`text-lg font-bold ${(analysis.gain_loss ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                      {(analysis.gain_loss ?? 0) >= 0 ? '+' : ''}₹{(analysis.gain_loss ?? 0).toFixed(2)}
                    </div>
                    <div className={`text-xs ${(analysis.gain_loss_percentage ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                      {(analysis.gain_loss_percentage ?? 0) >= 0 ? '+' : ''}{(analysis.gain_loss_percentage ?? 0).toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Technical Indicators */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-text flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    Technical Indicators
                  </h4>

                  {/* RSI */}
                  <RSIIndicator value={analysis.indicators?.rsi ?? 50} />

                  {/* MACD */}
                  <div className="bg-border/30 rounded-lg p-3">
                    <div className="text-xs text-muted mb-1">MACD</div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-xs text-muted">Value</div>
                        <div className={`text-sm font-semibold ${(analysis.indicators?.macd?.value ?? 0) > 0
                          ? 'text-green-600'
                          : 'text-red-600'
                          }`}>
                          {(analysis.indicators?.macd?.value ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted">Signal</div>
                        <div className="text-sm font-semibold text-text">
                          {(analysis.indicators?.macd?.signal ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted">Histogram</div>
                        <div className={`text-sm font-semibold ${(analysis.indicators?.macd?.histogram ?? 0) > 0
                          ? 'text-green-600'
                          : 'text-red-600'
                          }`}>
                          {(analysis.indicators?.macd?.histogram ?? 0).toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Moving Averages */}
                  <div className="bg-border/30 rounded-lg p-3">
                    <div className="text-xs text-muted mb-2">Moving Averages</div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">SMA 20:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.moving_averages?.sma_20 ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">SMA 50:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.moving_averages?.sma_50 ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">SMA 200:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.moving_averages?.sma_200 ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bollinger Bands */}
                  <div className="bg-border/30 rounded-lg p-3">
                    <div className="text-xs text-muted mb-2">Bollinger Bands</div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">Upper:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.bollinger_bands?.upper ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">Middle:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.bollinger_bands?.middle ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted">Lower:</span>
                        <span className="font-semibold text-text">
                          ₹{(analysis.indicators?.bollinger_bands?.lower ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Volume Trend */}
                  <div className="flex items-center justify-between bg-border/30 rounded-lg p-3">
                    <span className="text-xs text-muted">Volume Trend</span>
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${(analysis.indicators?.volume?.trend ?? 'stable') === 'increasing'
                      ? 'bg-green-100 text-green-700'
                      : (analysis.indicators?.volume?.trend ?? 'stable') === 'decreasing'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}>
                      {analysis.indicators?.volume?.trend ?? 'stable'}
                    </span>
                  </div>
                </div>

                {/* AI Signals */}
                <div className="space-y-3 pt-3 border-t border-border">
                  <h4 className="text-sm font-semibold text-text flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    AI Technical Signals
                  </h4>

                  {/* Recommendation Badge */}
                  <div className="text-center">
                    <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold border-2 ${getRecommendationColor(analysis.recommendation ?? 'hold')
                      }`}>
                      {getRecommendationIcon(analysis.recommendation ?? 'hold')}
                      {(analysis.recommendation ?? 'hold').replace('_', ' ').toUpperCase()}
                    </span>
                    <div className="text-xs text-muted mt-2">
                      Technical Signal Summary
                    </div>
                  </div>

                  {/* Bullish vs Bearish */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-3 text-center border border-green-200 dark:border-green-800">
                      <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400 mx-auto mb-1" />
                      <div className="text-xs text-muted">Bullish Factors</div>
                      <div className="text-lg font-bold text-green-600 dark:text-green-400">
                        {analysis.bullish_factors ?? 0}
                      </div>
                    </div>
                    <div className="bg-red-50 dark:bg-red-950/20 rounded-lg p-3 text-center border border-red-200 dark:border-red-800">
                      <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400 mx-auto mb-1" />
                      <div className="text-xs text-muted">Bearish Factors</div>
                      <div className="text-lg font-bold text-red-600 dark:text-red-400">
                        {analysis.bearish_factors ?? 0}
                      </div>
                    </div>
                  </div>

                  {/* Reasoning */}
                  <div className="bg-indigo-50 dark:bg-indigo-950/20 rounded-lg p-3 border border-indigo-200 dark:border-indigo-800">
                    <div className="text-xs font-semibold text-indigo-900 dark:text-indigo-300 mb-2">Key Insights</div>
                    <ul className="space-y-1">
                      {(analysis.signals ?? []).map((signal, idx) => (
                        <li key={idx} className="text-xs text-indigo-700 dark:text-indigo-300 flex items-start gap-1">
                          <span className="text-indigo-400 dark:text-indigo-500 mt-0.5">•</span>
                          <span>{signal}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
