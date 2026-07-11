import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SolverParamsPanel } from '../SolverParamsPanel';
import type { SolverParams } from '@/types';

const baseParams: SolverParams = {
  fuel_price: 7.5,
  hourly_wage: 30,
  carbon_price: 0.12,
  late_penalty_per_min: 5,
  search_time_limit: 60,
  use_multi_strategy: true,
  use_parallel: false,
  strategy_weights: {
    min_distance: 0.25,
    min_vehicles: 0.25,
    min_cost: 0.25,
    min_emission: 0.25,
  },
};

describe('SolverParamsPanel', () => {
  it('renders all parameter fields and switches', () => {
    render(<SolverParamsPanel params={baseParams} onParamsChange={vi.fn()} />);

    expect(screen.getByLabelText('油价 (元/升)')).toBeInTheDocument();
    expect(screen.getByLabelText('启用多策略')).toBeInTheDocument();
    expect(screen.getByLabelText('并行求解')).toBeInTheDocument();
  });

  it('calls onParamsChange when a number input changes', async () => {
    const onParamsChange = vi.fn();
    render(
      <SolverParamsPanel params={baseParams} onParamsChange={onParamsChange} />
    );

    const fuelInput = screen.getByLabelText('油价 (元/升)');
    fireEvent.change(fuelInput, { target: { value: '8.5' } });

    expect(onParamsChange).toHaveBeenCalledWith({ fuel_price: 8.5 });
  });

  it('calls onParamsChange when the multi-strategy switch is toggled off', async () => {
    const onParamsChange = vi.fn();
    render(
      <SolverParamsPanel params={baseParams} onParamsChange={onParamsChange} />
    );

    const switchEl = screen.getByLabelText('启用多策略');
    await userEvent.click(switchEl);

    expect(onParamsChange).toHaveBeenCalledWith({ use_multi_strategy: false });
  });

  it('does not access any store, context, or external hooks', () => {
    const onParamsChange = vi.fn();
    const { container } = render(
      <SolverParamsPanel params={baseParams} onParamsChange={onParamsChange} />
    );

    expect(container.firstChild).toBeTruthy();
  });

  it('renders strategy weight sliders when use_multi_strategy is true', () => {
    render(<SolverParamsPanel params={baseParams} onParamsChange={vi.fn()} />);

    expect(screen.getByText('策略权重')).toBeInTheDocument();
    expect(
      screen.getByRole('slider', { name: 'min_distance 权重' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('slider', { name: 'min_vehicles 权重' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('slider', { name: 'min_cost 权重' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('slider', { name: 'min_emission 权重' })
    ).toBeInTheDocument();
  });

  it('updates only the changed strategy weight via slider', async () => {
    const onParamsChange = vi.fn();
    render(
      <SolverParamsPanel params={baseParams} onParamsChange={onParamsChange} />
    );

    const distanceSlider = screen.getByRole('slider', {
      name: 'min_distance 权重',
    });
    await userEvent.click(distanceSlider);
    await userEvent.keyboard('{ArrowRight}');

    expect(onParamsChange).toHaveBeenCalledTimes(1);
    expect(onParamsChange).toHaveBeenCalledWith({
      strategy_weights: {
        min_distance: 0.3,
        min_vehicles: 0.25,
        min_cost: 0.25,
        min_emission: 0.25,
      },
    });
  });

  it('hides strategy weight sliders when use_multi_strategy is false', () => {
    render(
      <SolverParamsPanel
        params={{ ...baseParams, use_multi_strategy: false }}
        onParamsChange={vi.fn()}
      />
    );

    expect(screen.queryByText('策略权重')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('slider', { name: 'min_distance 权重' })
    ).not.toBeInTheDocument();
  });
});
