# Frontend API Usage Guide - Installment Payments

## Complete Integration Guide for Next.js Frontend

**Created:** 2025-11-25
**For:** CSF Frontend Team
**Backend Version:** Milestone 3+

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Client Setup](#api-client-setup)
3. [TypeScript Types](#typescript-types)
4. [User Flows](#user-flows)
5. [React Hooks](#react-hooks)
6. [Component Examples](#component-examples)
7. [Error Handling](#error-handling)
8. [Testing](#testing)

---

## Quick Start

### Installation

```bash
# Install dependencies
npm install axios react-query
# or
pnpm add axios react-query
```

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

---

## API Client Setup

### Base API Client (`lib/api-client.ts`)

```typescript
import axios, { AxiosError, AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token interceptor
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle token refresh or redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  get = <T = any>(url: string, params?: any) =>
    this.client.get<T>(url, { params });

  post = <T = any>(url: string, data?: any) =>
    this.client.post<T>(url, data);

  put = <T = any>(url: string, data?: any) =>
    this.client.put<T>(url, data);

  delete = <T = any>(url: string) =>
    this.client.delete<T>(url);
}

export const apiClient = new APIClient();
```

---

## TypeScript Types

### Core Types (`types/installments.ts`)

```typescript
export type InstallmentFrequency = 'weekly' | 'biweekly' | 'monthly';

export type InstallmentPlanStatus =
  | 'active'
  | 'completed'
  | 'cancelled'
  | 'defaulted';

export type InstallmentPaymentStatus =
  | 'pending'
  | 'paid'
  | 'failed'
  | 'skipped';

export interface InstallmentPlan {
  id: string;
  order_id: string;
  user_id: string;
  total_amount: string; // Decimal as string
  num_installments: number;
  installment_amount: string; // Decimal as string
  frequency: InstallmentFrequency;
  start_date: string; // ISO date
  stripe_subscription_id: string | null;
  status: InstallmentPlanStatus;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface InstallmentPayment {
  id: string;
  installment_plan_id: string;
  payment_id: string | null;
  installment_number: number;
  due_date: string; // ISO date
  amount: string; // Decimal as string
  status: InstallmentPaymentStatus;
  paid_at: string | null; // ISO datetime
  attempt_count: number;
}

export interface InstallmentScheduleItem {
  installment_number: number;
  due_date: string; // ISO date
  amount: string; // Decimal as string
}

export interface InstallmentSchedulePreview {
  total_amount: string;
  num_installments: number;
  frequency: InstallmentFrequency;
  schedule: InstallmentScheduleItem[];
}

export interface CreateInstallmentPlanRequest {
  order_id: string;
  num_installments: number;
  frequency: InstallmentFrequency;
  payment_method_id: string;
}
```

---

## User Flows

### Flow 1: Complete Checkout with Installments

```typescript
// lib/installment-api.ts

import { apiClient } from './api-client';
import {
  InstallmentPlan,
  InstallmentSchedulePreview,
  CreateInstallmentPlanRequest,
} from '@/types/installments';

export class InstallmentAPI {
  /**
   * Step 1: Preview installment schedule
   */
  static async previewSchedule(params: {
    orderId: string;
    numInstallments: number;
    frequency: string;
    startDate?: string;
  }): Promise<InstallmentSchedulePreview> {
    const { data } = await apiClient.post<InstallmentSchedulePreview>(
      '/installments/preview',
      null,
      { params }
    );
    return data;
  }

  /**
   * Step 2: Create installment plan
   */
  static async createPlan(
    request: CreateInstallmentPlanRequest
  ): Promise<InstallmentPlan> {
    const { data } = await apiClient.post<InstallmentPlan>(
      '/installments/',
      request
    );
    return data;
  }

  /**
   * Get user's installment plans
   */
  static async getMyPlans(
    status?: string
  ): Promise<InstallmentPlan[]> {
    const { data } = await apiClient.get<InstallmentPlan[]>(
      '/installments/my',
      { status }
    );
    return data;
  }

  /**
   * Get plan details
   */
  static async getPlan(planId: string): Promise<InstallmentPlan> {
    const { data } = await apiClient.get<InstallmentPlan>(
      `/installments/${planId}`
    );
    return data;
  }

  /**
   * Get payment schedule
   */
  static async getSchedule(
    planId: string
  ): Promise<InstallmentPayment[]> {
    const { data } = await apiClient.get<InstallmentPayment[]>(
      `/installments/${planId}/schedule`
    );
    return data;
  }

  /**
   * Get upcoming payments
   */
  static async getUpcoming(
    daysAhead: number = 7
  ): Promise<InstallmentPayment[]> {
    const { data } = await apiClient.get<InstallmentPayment[]>(
      '/installments/upcoming/due',
      { days_ahead: daysAhead }
    );
    return data;
  }

  /**
   * Cancel plan
   */
  static async cancelPlan(planId: string): Promise<InstallmentPlan> {
    const { data } = await apiClient.post<InstallmentPlan>(
      `/installments/${planId}/cancel`
    );
    return data;
  }
}
```

---

## React Hooks

### Custom Hooks (`hooks/use-installments.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-hot-toast';
import { InstallmentAPI } from '@/lib/installment-api';

/**
 * Hook to preview installment schedule
 */
export function usePreviewInstallments(params: {
  orderId: string;
  numInstallments: number;
  frequency: string;
  startDate?: string;
}) {
  return useQuery(
    ['installment-preview', params],
    () => InstallmentAPI.previewSchedule(params),
    {
      enabled: !!params.orderId && params.numInstallments >= 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
}

/**
 * Hook to create installment plan
 */
export function useCreateInstallmentPlan() {
  const queryClient = useQueryClient();

  return useMutation(
    (data: CreateInstallmentPlanRequest) =>
      InstallmentAPI.createPlan(data),
    {
      onSuccess: (plan) => {
        toast.success('Installment plan created successfully!');
        queryClient.invalidateQueries('my-installment-plans');
        queryClient.invalidateQueries('upcoming-installments');
      },
      onError: (error: any) => {
        const message = error.response?.data?.message ||
          'Failed to create installment plan';
        toast.error(message);
      },
    }
  );
}

/**
 * Hook to fetch user's installment plans
 */
export function useMyInstallmentPlans(status?: string) {
  return useQuery(
    ['my-installment-plans', status],
    () => InstallmentAPI.getMyPlans(status),
    {
      staleTime: 2 * 60 * 1000, // 2 minutes
    }
  );
}

/**
 * Hook to fetch plan details
 */
export function useInstallmentPlan(planId: string) {
  return useQuery(
    ['installment-plan', planId],
    () => InstallmentAPI.getPlan(planId),
    {
      enabled: !!planId,
    }
  );
}

/**
 * Hook to fetch payment schedule
 */
export function usePaymentSchedule(planId: string) {
  return useQuery(
    ['payment-schedule', planId],
    () => InstallmentAPI.getSchedule(planId),
    {
      enabled: !!planId,
    }
  );
}

/**
 * Hook to fetch upcoming payments
 */
export function useUpcomingPayments(daysAhead: number = 7) {
  return useQuery(
    ['upcoming-installments', daysAhead],
    () => InstallmentAPI.getUpcoming(daysAhead),
    {
      refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    }
  );
}

/**
 * Hook to cancel installment plan
 */
export function useCancelInstallmentPlan() {
  const queryClient = useQueryClient();

  return useMutation(
    (planId: string) => InstallmentAPI.cancelPlan(planId),
    {
      onSuccess: () => {
        toast.success('Installment plan cancelled');
        queryClient.invalidateQueries('my-installment-plans');
        queryClient.invalidateQueries('upcoming-installments');
      },
      onError: (error: any) => {
        const message = error.response?.data?.message ||
          'Failed to cancel plan';
        toast.error(message);
      },
    }
  );
}
```

---

## Component Examples

### 1. Checkout - Installment Preview

```typescript
// components/checkout/InstallmentPreview.tsx

'use client';

import { useState } from 'react';
import { usePreviewInstallments } from '@/hooks/use-installments';
import { format, parseISO } from 'date-fns';

interface Props {
  orderId: string;
  orderTotal: number;
  onSelectPlan: (numInstallments: number, frequency: string) => void;
}

export function InstallmentPreview({
  orderId,
  orderTotal,
  onSelectPlan
}: Props) {
  const [numInstallments, setNumInstallments] = useState(3);
  const [frequency, setFrequency] = useState<string>('monthly');

  const { data: preview, isLoading } = usePreviewInstallments({
    orderId,
    numInstallments,
    frequency,
  });

  if (isLoading) {
    return <div className="animate-pulse">Loading schedule...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {/* Number of Payments */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Number of Payments
          </label>
          <select
            value={numInstallments}
            onChange={(e) => setNumInstallments(Number(e.target.value))}
            className="w-full px-3 py-2 border rounded-md"
          >
            {[2, 3, 4, 6, 12].map((num) => (
              <key={num} value={num}>
                {num} payments
              </option>
            ))}
          </select>
        </div>

        {/* Frequency */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Frequency
          </label>
          <select
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every 2 Weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      {/* Payment Schedule */}
      {preview && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-semibold mb-4">Payment Schedule</h3>
          <div className="space-y-2">
            {preview.schedule.map((item) => (
              <div
                key={item.installment_number}
                className="flex justify-between items-center py-2 border-b last:border-0"
              >
                <span className="text-sm">
                  Payment {item.installment_number} of {preview.num_installments}
                </span>
                <div className="text-right">
                  <div className="font-semibold">
                    ${item.amount}
                  </div>
                  <div className="text-xs text-gray-500">
                    Due {format(parseISO(item.due_date), 'MMM d, yyyy')}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t">
            <div className="flex justify-between font-semibold">
              <span>Total</span>
              <span>${preview.total_amount}</span>
            </div>
          </div>

          <button
            onClick={() => onSelectPlan(numInstallments, frequency)}
            className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
          >
            Select This Plan
          </button>
        </div>
      )}
    </div>
  );
}
```

### 2. Payment Method with Installments

```typescript
// components/checkout/InstallmentCheckout.tsx

'use client';

import { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';
import { useCreateInstallmentPlan } from '@/hooks/use-installments';

const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);

interface Props {
  orderId: string;
  numInstallments: number;
  frequency: string;
  onSuccess: () => void;
}

function CheckoutForm({ orderId, numInstallments, frequency, onSuccess }: Props) {
  const stripe = useStripe();
  const elements = useElements();
  const createPlan = useCreateInstallmentPlan();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) return;

    setIsProcessing(true);

    try {
      // Submit payment element to get payment method
      const { error: submitError } = await elements.submit();
      if (submitError) throw submitError;

      // Create payment method
      const { error, paymentMethod } = await stripe.createPaymentMethod({
        elements,
      });

      if (error) throw error;

      // Create installment plan
      await createPlan.mutateAsync({
        order_id: orderId,
        num_installments: numInstallments,
        frequency: frequency as any,
        payment_method_id: paymentMethod.id,
      });

      onSuccess();
    } catch (error: any) {
      console.error('Payment failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <PaymentElement />

      <button
        type="submit"
        disabled={!stripe || isProcessing}
        className="w-full bg-green-600 text-white py-3 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
      >
        {isProcessing ? 'Processing...' : 'Confirm Installment Plan'}
      </button>
    </form>
  );
}

export function InstallmentCheckout(props: Props) {
  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm {...props} />
    </Elements>
  );
}
```

### 3. My Installment Plans Dashboard

```typescript
// components/dashboard/InstallmentPlans.tsx

'use client';

import { useMyInstallmentPlans, useCancelInstallmentPlan } from '@/hooks/use-installments';
import { format, parseISO } from 'date-fns';

export function InstallmentPlans() {
  const { data: plans, isLoading } = useMyInstallmentPlans();
  const cancelPlan = useCancelInstallmentPlan();

  if (isLoading) {
    return <div>Loading your payment plans...</div>;
  }

  if (!plans || plans.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No installment plans yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {plans.map((plan) => (
        <div
          key={plan.id}
          className="border rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="font-semibold text-lg">
                {plan.num_installments} Payment Plan
              </h3>
              <p className="text-sm text-gray-500">
                {plan.frequency} · Started {format(parseISO(plan.start_date), 'MMM d, yyyy')}
              </p>
            </div>

            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                plan.status === 'active'
                  ? 'bg-green-100 text-green-800'
                  : plan.status === 'completed'
                  ? 'bg-blue-100 text-blue-800'
                  : plan.status === 'cancelled'
                  ? 'bg-gray-100 text-gray-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {plan.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-500">Total Amount</p>
              <p className="font-semibold">${plan.total_amount}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Per Payment</p>
              <p className="font-semibold">${plan.installment_amount}</p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => window.location.href = `/installments/${plan.id}`}
              className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              View Schedule
            </button>

            {plan.status === 'active' && (
              <button
                onClick={() => {
                  if (confirm('Are you sure you want to cancel this plan?')) {
                    cancelPlan.mutate(plan.id);
                  }
                }}
                className="px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200"
              >
                Cancel Plan
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 4. Upcoming Payments Widget

```typescript
// components/dashboard/UpcomingPayments.tsx

'use client';

import { useUpcomingPayments } from '@/hooks/use-installments';
import { format, parseISO, differenceInDays } from 'date-fns';

export function UpcomingPayments() {
  const { data: upcoming, isLoading } = useUpcomingPayments(30);

  if (isLoading) {
    return <div className="animate-pulse h-32 bg-gray-100 rounded-lg" />;
  }

  if (!upcoming || upcoming.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 text-center">
        <p className="text-gray-500">No upcoming payments</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Upcoming Payments</h2>

      <div className="space-y-3">
        {upcoming.slice(0, 5).map((payment) => {
          const daysUntil = differenceInDays(
            parseISO(payment.due_date),
            new Date()
          );

          return (
            <div
              key={payment.id}
              className="flex justify-between items-center p-3 bg-gray-50 rounded-md"
            >
              <div>
                <p className="font-medium">
                  Payment {payment.installment_number}
                </p>
                <p className="text-sm text-gray-500">
                  Due {format(parseISO(payment.due_date), 'MMM d, yyyy')}
                  {daysUntil <= 3 && (
                    <span className="ml-2 text-orange-600 font-medium">
                      • {daysUntil} days
                    </span>
                  )}
                </p>
              </div>

              <div className="text-right">
                <p className="font-semibold">${payment.amount}</p>
                <span
                  className={`text-xs px-2 py-1 rounded ${
                    payment.status === 'paid'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}
                >
                  {payment.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

## Error Handling

### Error Types

```typescript
// types/errors.ts

export interface APIError {
  error_code: string;
  message: string;
  data?: Record<string, any>;
}

export const handleAPIError = (error: any): string => {
  if (error.response?.data?.message) {
    return error.response.data.message;
  }

  if (error.message) {
    return error.message;
  }

  return 'An unexpected error occurred';
};
```

### Common Error Messages

| Error | Message | User Action |
|-------|---------|-------------|
| 400 | "Installment amount below minimum ($10)" | Reduce number of installments |
| 400 | "Cannot create for paid order" | Order already completed |
| 403 | "Permission denied" | User doesn't own resource |
| 404 | "Order not found" | Invalid order ID |
| 401 | "Unauthorized" | Re-authenticate |

---

## Testing

### Mock Data for Testing

```typescript
// __mocks__/installments.ts

export const mockInstallmentPlan = {
  id: 'plan_123',
  order_id: 'order_456',
  user_id: 'user_789',
  total_amount: '600.00',
  num_installments: 3,
  installment_amount: '200.00',
  frequency: 'monthly' as const,
  start_date: '2025-12-01',
  stripe_subscription_id: 'sub_123',
  status: 'active' as const,
  created_at: '2025-11-25T10:00:00Z',
  updated_at: '2025-11-25T10:00:00Z',
};

export const mockSchedulePreview = {
  total_amount: '600.00',
  num_installments: 3,
  frequency: 'monthly' as const,
  schedule: [
    {
      installment_number: 1,
      due_date: '2025-12-01',
      amount: '200.00',
    },
    {
      installment_number: 2,
      due_date: '2025-12-31',
      amount: '200.00',
    },
    {
      installment_number: 3,
      due_date: '2026-01-30',
      amount: '200.00',
    },
  ],
};
```

---

## Summary

### Key Points for Frontend Team

1. **Always Preview First**: Show users the schedule before creating plan
2. **Stripe Integration**: Use Stripe Elements for payment method
3. **Real-time Updates**: Use React Query for automatic refresh
4. **Error Handling**: Show user-friendly error messages
5. **Loading States**: Always handle loading/error states
6. **Mobile Friendly**: All components should be responsive

### API Endpoints Quick Reference

```
POST   /installments/preview           - Preview schedule
POST   /installments/                  - Create plan
GET    /installments/my                - List user's plans
GET    /installments/{id}              - Get plan details
GET    /installments/{id}/schedule     - Get payment schedule
GET    /installments/upcoming/due      - Get upcoming payments
POST   /installments/{id}/cancel       - Cancel plan
```

### Next Steps

1. Implement components in your frontend
2. Test with Stripe test mode
3. Add error boundaries
4. Implement analytics tracking
5. Add loading skeletons

---

**Documentation Version:** 1.0
**Last Updated:** 2025-11-25
**Contact:** Backend Team
