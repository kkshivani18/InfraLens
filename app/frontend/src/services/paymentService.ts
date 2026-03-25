// Payment Service - Handles all Razorpay payment operations | Communicates with backend payment endpoints

import { useAuth } from '@clerk/clerk-react';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// to get auth token
export async function getAuthToken(): Promise<string | null> {
  try {
    return sessionStorage.getItem('clerk_token') || null;
  } catch {
    return null;
  }
}

export type PlanType = 'pro' | 'team';

export interface CreateSubscriptionResponse {
  razorpay_subscription_id: string;
  razorpay_key_id: string;
  amount: number;
  currency: string;
  customer_email: string;
  customer_id: string;
}

export interface SubscriptionStatus {
  plan: 'free' | 'pro' | 'team';
  status: 'active' | 'inactive' | 'pending' | 'past_due' | 'cancelled';
  current_period_end: string | null;
  razorpay_subscription_id: string | null;
}

// Create a subscription checkout | Returns payload needed to launch Razorpay modal
export async function createSubscription(
  plan: PlanType,
  token?: string
): Promise<CreateSubscriptionResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_URL}/api/payments/create-subscription`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({ plan }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create subscription');
  }

  return response.json();
}

// Get current subscription status | Check if subscription is active and when it expires
export async function getSubscriptionStatus(token?: string): Promise<SubscriptionStatus> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_URL}/api/payments/subscription-status`,
    {
      method: 'GET',
      headers,
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch subscription status');
  }

  return response.json();
}


//  Launch Razorpay Checkout Modal | This opens the payment experience
export function launchRazorpayCheckout(
  payload: CreateSubscriptionResponse,
  onSuccess: () => void,
  onError: (error: string) => void
): void {
  // checks if Razorpay script is loaded
  if (!window.Razorpay) {
    onError('Razorpay SDK not loaded');
    return;
  }

  const options = {
    key: payload.razorpay_key_id,
    subscription_id: payload.razorpay_subscription_id,
    name: 'InfraLens',
    description: 'Code Analysis & Documentation Tool',
    image: 'https://infralens-theta.vercel.app/logo.png',
    amount: payload.amount,
    currency: payload.currency,
    customer_email: payload.customer_email,
    
    // success - user completed the flow
    handler: function (response: { razorpay_payment_id: string }) {
      console.log('✅ Payment successful:', response.razorpay_payment_id);
      onSuccess();
    },
    
    modal: {
      ondismiss: function () {
        onError('Payment cancelled by user');
      },
    },
  };

  const rzp = new window.Razorpay(options);
  
  // Custom error handler
  rzp.on('payment.failed', function (response: { error: { code: string; description: string } }) {
    onError(`Payment failed: ${response.error.description}`);
  });

  rzp.open();
}

// Retry payment for failed subscription
export async function retryPayment(plan: PlanType): Promise<void> {
  try {
    const payload = await createSubscription(plan);
    launchRazorpayCheckout(
      payload,
      () => {
        console.log('Subscription successful');
        // Redirect or update UI
        window.location.href = '/pricing/success';
      },
      (error) => {
        console.error('Payment error:', error);
        throw new Error(error);
      }
    );
  } catch (error) {
    console.error('Failed to retry payment:', error);
    throw error;
  }
}
