import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TradingJournalForm } from '../TradingJournalForm'

describe('TradingJournalForm', () => {
    const mockOnSubmit = vi.fn()
    const mockOnCancel = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders form fields correctly in create mode', () => {
        render(
            <TradingJournalForm
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                mode="create"
            />
        )

        expect(screen.getByLabelText(/symbol \*/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/quantity \*/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/entry price \*/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/entry date \*/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/exit price/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/exit date/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/notes/i)).toBeInTheDocument()
    })

    it('renders form fields correctly in update mode', () => {
        render(
            <TradingJournalForm
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                mode="update"
            />
        )

        // Symbol, quantity, entry price, entry date should not be in update mode
        expect(screen.queryByLabelText(/symbol \*/i)).not.toBeInTheDocument()
        expect(screen.queryByLabelText(/quantity \*/i)).not.toBeInTheDocument()
        expect(screen.queryByLabelText(/entry price \*/i)).not.toBeInTheDocument()
        expect(screen.queryByLabelText(/entry date \*/i)).not.toBeInTheDocument()

        // Exit fields should still be present
        expect(screen.getByLabelText(/exit price/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/exit date/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/notes/i)).toBeInTheDocument()
    })

    it('calls onSubmit with correct data when form is submitted', () => {
        render(
            <TradingJournalForm
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                mode="create"
            />
        )

        fireEvent.change(screen.getByLabelText(/symbol \*/i), { target: { value: 'RELIANCE.NS' } })
        fireEvent.change(screen.getByLabelText(/quantity \*/i), { target: { value: '10' } })
        fireEvent.change(screen.getByLabelText(/entry price \*/i), { target: { value: '2500.00' } })
        fireEvent.change(screen.getByLabelText(/entry date \*/i), { target: { value: '2024-06-01T10:00' } })

        fireEvent.click(screen.getByText(/save trade/i))

        expect(mockOnSubmit).toHaveBeenCalledTimes(1)
        expect(mockOnSubmit).toHaveBeenCalledWith({
            symbol: 'RELIANCE.NS',
            entry_price: 2500,
            exit_price: null,
            quantity: 10,
            entry_date: '2024-06-01T10:00',
            exit_date: null,
            notes: null
        })
    })

    it('calls onCancel when cancel button is clicked', () => {
        render(
            <TradingJournalForm
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                mode="create"
            />
        )

        fireEvent.click(screen.getByText(/cancel/i))

        expect(mockOnCancel).toHaveBeenCalledTimes(1)
        expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('disables submit button when loading', () => {
        render(
            <TradingJournalForm
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                isLoading={true}
                mode="create"
            />
        )

        const submitButton = screen.getByText(/saving.../i)
        expect(submitButton).toBeDisabled()
    })

    it('pre-fills initial data when provided', () => {
        render(
            <TradingJournalForm
                initialData={{
                    symbol: 'TCS.NS',
                    entry_price: 3500,
                    quantity: 5,
                    entry_date: '2024-06-01T10:00',
                    exit_price: 3400,
                    notes: 'Test trade'
                }}
                onSubmit={mockOnSubmit}
                onCancel={mockOnCancel}
                mode="create"
            />
        )

        expect(screen.getByLabelText(/symbol \*/i)).toHaveValue('TCS.NS')
        expect(screen.getByLabelText(/quantity \*/i)).toHaveValue('5')
        expect(screen.getByLabelText(/entry price \*/i)).toHaveValue('3500')
        expect(screen.getByLabelText(/exit price/i)).toHaveValue('3400')
        expect(screen.getByLabelText(/notes/i)).toHaveValue('Test trade')
    })
})
