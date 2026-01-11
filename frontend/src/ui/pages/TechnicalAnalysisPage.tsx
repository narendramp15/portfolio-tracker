import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../lib/api';
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
  volume_trend: string;
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
  confidence: number;
  signals: string[];
  bullish_factors: number;
  bearish_factors: number;
}

// Helper functions
const getRecommendationColor = (recommendation: string): string => {
  switch (recommendation) {
    case 'strong_buy': return 'text-green-600 bg-green-50 border-green-200';
    case 'buy': return 'text-green-600 bg-green-50 border-green-200';
    case 'hold': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'sell': return 'text-red-600 bg-red-50 border-red-200';
    case 'strong_sell': return 'text-red-600 bg-red-50 border-red-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

const getRecommendationIcon = (recommendation: string) => {
  switch (recommendation) {
    case 'strong_buy':
    case 'buy':
      return <ArrowUpRight className="w-4 h-4" />;
    case 'sell':
    case 'strong_sell':
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
        <span className="text-gray-600">RSI: {value.toFixed(1)}</span>
        <span className={`font-medium ${value < 30 ? 'text-green-600' : value > 70 ? 'text-red-600' : 'text-yellow-600'
          }`}>
          {getLabel()}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
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
        <div className="text-gray-600">Loading technical analysis...</div>
      </div>
    );
  }

  if (!analyses || analyses.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">No holdings found for analysis</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Technical Analysis & AI Recommendations
          </h1>
          <p className="text-gray-600 mt-1">
            AI-powered technical analysis with buy/sell signals
          </p>
        </div>

        {/* View Toggle Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('table')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${viewMode === 'table'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md'
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
              }`}
          >
            <LayoutList className="w-4 h-4" />
            Table View
          </button>
          <button
            onClick={() => setViewMode('cards')}
            className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${viewMode === 'cards'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md'
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
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
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Asset
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Price
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    RSI
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    MACD
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    AI Recommendation
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {analyses.map((analysis) => (
                  <tr key={analysis.asset_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-gray-900">{analysis.symbol}</div>
                        <div className="text-sm text-gray-600">{analysis.name}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="font-medium text-gray-900">
                        ₹{(analysis.current_price ?? 0).toFixed(2)}
                      </div>
                      <div className="text-sm text-gray-600">
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
                      <div className="text-xs text-gray-600">
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
                        <span className="text-xs text-gray-600">
                          {(analysis.confidence ?? 0).toFixed(0)}% confidence
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
              className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
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
                    <div className="text-xs text-gray-600 mb-1">Current Price</div>
                    <div className="text-lg font-bold text-gray-900">
                      ₹{(analysis.current_price ?? 0).toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-600">Qty: {analysis.quantity ?? 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600 mb-1">P&L</div>
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
                  <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    Technical Indicators
                  </h4>

                  {/* RSI */}
                  <RSIIndicator value={analysis.indicators?.rsi ?? 50} />

                  {/* MACD */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-600 mb-1">MACD</div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-xs text-gray-500">Value</div>
                        <div className={`text-sm font-semibold ${(analysis.indicators?.macd?.value ?? 0) > 0
                            ? 'text-green-600'
                            : 'text-red-600'
                          }`}>
                          {(analysis.indicators?.macd?.value ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Signal</div>
                        <div className="text-sm font-semibold text-gray-900">
                          {(analysis.indicators?.macd?.signal ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Histogram</div>
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
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-600 mb-2">Moving Averages</div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">SMA 20:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.moving_averages?.sma_20 ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">SMA 50:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.moving_averages?.sma_50 ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">SMA 200:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.moving_averages?.sma_200 ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bollinger Bands */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-600 mb-2">Bollinger Bands</div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">Upper:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.bollinger_bands?.upper ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">Middle:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.bollinger_bands?.middle ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-600">Lower:</span>
                        <span className="font-semibold text-gray-900">
                          ₹{(analysis.indicators?.bollinger_bands?.lower ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Volume Trend */}
                  <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                    <span className="text-xs text-gray-600">Volume Trend</span>
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
                <div className="space-y-3 pt-3 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    AI Recommendation
                  </h4>

                  {/* Recommendation Badge */}
                  <div className="text-center">
                    <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold border-2 ${getRecommendationColor(analysis.recommendation ?? 'hold')
                      }`}>
                      {getRecommendationIcon(analysis.recommendation ?? 'hold')}
                      {(analysis.recommendation ?? 'hold').replace('_', ' ').toUpperCase()}
                    </span>
                    <div className="text-xs text-gray-600 mt-2">
                      Confidence: {(analysis.confidence ?? 0).toFixed(0)}%
                    </div>
                  </div>

                  {/* Bullish vs Bearish */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-green-50 rounded-lg p-3 text-center border border-green-200">
                      <TrendingUp className="w-5 h-5 text-green-600 mx-auto mb-1" />
                      <div className="text-xs text-gray-600">Bullish Factors</div>
                      <div className="text-lg font-bold text-green-600">
                        {analysis.bullish_factors ?? 0}
                      </div>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3 text-center border border-red-200">
                      <TrendingDown className="w-5 h-5 text-red-600 mx-auto mb-1" />
                      <div className="text-xs text-gray-600">Bearish Factors</div>
                      <div className="text-lg font-bold text-red-600">
                        {analysis.bearish_factors ?? 0}
                      </div>
                    </div>
                  </div>

                  {/* Reasoning */}
                  <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                    <div className="text-xs font-semibold text-indigo-900 mb-2">Key Insights</div>
                    <ul className="space-y-1">
                      {(analysis.signals ?? []).map((signal, idx) => (
                        <li key={idx} className="text-xs text-indigo-700 flex items-start gap-1">
                          <span className="text-indigo-400 mt-0.5">•</span>
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
