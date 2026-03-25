/**
 * Pricing Page Component
 * Shows Free / Pro / Team plans with upgrade buttons
 */

import React,{ useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import {
  createSubscription,
  launchRazorpayCheckout,
  type PlanType,
  getSubscriptionStatus,
} from '../services/paymentService';

interface PricingTier {
  name: PlanType | 'free';
  displayName: string;
  price: number;
  currency: string;
  description: string;
  features: string[];
  cta: string;
  ctaStyle: 'primary' | 'secondary';
  highlighted?: boolean;
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: 'free',
    displayName: 'Free',
    price: 0,
    currency: '₹',
    description: 'Perfect for exploring InfraLens',
    features: [
      'Clone & analyze repositories',
      'Chat with codebase AI',
      'View chat history',
      'Up to 10 repos',
      'Basic support',
    ],
    cta: 'Get Started',
    ctaStyle: 'secondary',
  },
  {
    name: 'pro',
    displayName: 'Pro',
    price: 100,
    currency: '₹',
    description: 'For individual developers',
    features: [
      'Everything in Free',
      'Share chat sessions (up to 5)',
      'Priority support',
      'Unlimited repos',
      'Advanced analytics',
      'API access',
    ],
    cta: 'Upgrade to Pro',
    ctaStyle: 'primary',
    highlighted: true,
  },
  {
    name: 'team',
    displayName: 'Team',
    price: 250,
    currency: '₹',
    description: 'For teams & organizations',
    features: [
      'Everything in Pro',
      'Share chat sessions (up to 20)',
      'Team management',
      'Team analytics dashboard',
      'Dedicated support',
      'Custom integrations',
    ],
    cta: 'Upgrade to Team',
    ctaStyle: 'primary',
  },
];

interface CheckoutState {
  loading: boolean;
  error: string | null;
  selectedPlan: PlanType | null;
}

export function PricingPage() {
  const { isSignedIn, getToken } = useAuth();
  const navigate = useNavigate();
  const [checkout, setCheckout] = useState<CheckoutState>({
    loading: false,
    error: null,
    selectedPlan: null,
  });
  const [currentSubscription, setCurrentSubscription] = useState<{
    plan: string;
    status: string;
  } | null>(null);

  // Fetch user's current subscription on mount
  React.useEffect(() => {
    if (isSignedIn) {
      fetchCurrentSubscription();
      
      // check if pending upgrade
      const pendingPlan = localStorage.getItem('pendingUpgradePlan') as PlanType | null;
      if (pendingPlan) {
        localStorage.removeItem('pendingUpgradePlan');
        // auto-trigger upgrade flow
        setTimeout(() => handleUpgrade(pendingPlan), 500);
      }
    }
  }, [isSignedIn]);

  async function fetchCurrentSubscription() {
    try {
      const token = await getToken();
      const subscription = await getSubscriptionStatus(token || undefined);
      setCurrentSubscription({
        plan: subscription.plan,
        status: subscription.status,
      });
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    }
  }

  async function handleUpgrade(plan: PlanType) {
    if (!isSignedIn) {
      // Store the plan intent in localStorage
      localStorage.setItem('pendingUpgradePlan', plan);
      // Redirect to sign up - Clerk will handle it
      navigate('/sign-up?redirect_url=/pricing');
      return;
    }

    setCheckout({ loading: true, error: null, selectedPlan: plan });

    try {
      const token = await getToken();
      
      // create subscription on backend
      const payload = await createSubscription(plan, token || undefined);

      // launch Razorpay checkout
      launchRazorpayCheckout(
        payload,
        () => {
          // On success: Refresh subscription status and redirect
          setCheckout({ loading: false, error: null, selectedPlan: null });
          fetchCurrentSubscription();
          navigate('/pricing/success', { state: { plan } });
        },
        (error) => {
          // On error: Show error message
          setCheckout({ loading: false, error, selectedPlan: null });
        }
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'An error occurred';
      setCheckout({
        loading: false,
        error: message,
        selectedPlan: null,
      });
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 py-12 px-4 sm:px-6 lg:px-8">
      {/* Header Section */}
      <div className="max-w-7xl mx-auto text-center mb-12">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">
          Simple, Transparent Pricing
        </h1>
        <p className="text-xl text-slate-300 mb-2">
          Choose the plan that fits your needs
        </p>
        <p className="text-slate-400">
          No hidden fees. Cancel anytime. Start free, upgrade later.
        </p>
      </div>

      {/* Current Subscription Info */}
      {isSignedIn && currentSubscription && (
        <div className="max-w-3xl mx-auto mb-12 p-4 bg-slate-700/50 border border-slate-600 rounded-lg">
          <p className="text-slate-200">
            Current Plan:{' '}
            <span className="font-semibold text-white capitalize">
              {currentSubscription.plan}
            </span>
            {currentSubscription.status !== 'active' && (
              <span className="ml-2 text-yellow-400">
                (Status: {currentSubscription.status})
              </span>
            )}
          </p>
        </div>
      )}

      {/* Error Message */}
      {checkout.error && (
        <div className="max-w-3xl mx-auto mb-8 p-4 bg-red-900/20 border border-red-500 text-red-200 rounded-lg">
          <p className="font-semibold">Payment Error</p>
          <p>{checkout.error}</p>
        </div>
      )}

      {/* Pricing Cards */}
      <div className="max-w-7xl mx-auto grid md:grid-cols-3 gap-8">
        {PRICING_TIERS.map((tier) => (
          <div
            key={tier.name}
            className={`relative rounded-2xl transition-all ${
              tier.highlighted
                ? 'md:scale-105 bg-gradient-to-br from-blue-600 to-blue-800 shadow-2xl'
                : 'bg-slate-800 shadow-lg hover:shadow-xl'
            }`}
          >
            {/* Badge for highlighted tier */}
            {tier.highlighted && (
              <div className="absolute -top-5 left-1/2 transform -translate-x-1/2">
                <span className="bg-yellow-400 text-slate-900 px-4 py-1 rounded-full text-sm font-bold">
                  Most Popular
                </span>
              </div>
            )}

            <div className="p-8">
              {/* Plan Header */}
              <h3 className={`text-2xl font-bold mb-2 ${
                tier.highlighted ? 'text-white' : 'text-slate-100'
              }`}>
                {tier.displayName}
              </h3>
              <p className={`text-sm mb-6 ${
                tier.highlighted ? 'text-blue-100' : 'text-slate-400'
              }`}>
                {tier.description}
              </p>

              {/* Pricing */}
              <div className="mb-6">
                <span className={`text-5xl font-bold ${
                  tier.highlighted ? 'text-white' : 'text-slate-100'
                }`}>
                  {tier.currency}{tier.price}
                </span>
                {tier.price > 0 && (
                  <span className={`text-sm ml-2 ${
                    tier.highlighted ? 'text-blue-100' : 'text-slate-400'
                  }`}>
                    /month
                  </span>
                )}
              </div>

              {/* CTA Button */}
              <button
                onClick={() => {
                  if (tier.name === 'free') {
                    navigate('/');
                  } else {
                    handleUpgrade(tier.name as PlanType);
                  }
                }}
                disabled={checkout.loading && checkout.selectedPlan === tier.name}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-all mb-8 ${
                  tier.highlighted
                    ? 'bg-white text-blue-600 hover:bg-slate-100 disabled:opacity-50'
                    : 'bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50'
                }`}
              >
                {checkout.loading && checkout.selectedPlan === tier.name
                  ? 'Processing...'
                  : tier.cta}
              </button>

              {/* Features List */}
              <div className="space-y-4">
                {tier.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <svg
                      className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                        tier.highlighted ? 'text-white' : 'text-green-400'
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className={tier.highlighted ? 'text-white' : 'text-slate-300'}>
                      {feature}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* FAQ Section */}
      <div className="max-w-3xl mx-auto mt-16 pt-12 border-t border-slate-700">
        <h2 className="text-2xl font-bold text-white mb-8 text-center">
          Frequently Asked Questions
        </h2>
        <div className="space-y-6">
          <details className="bg-slate-800 p-6 rounded-lg cursor-pointer">
            <summary className="text-lg font-semibold text-white">
              Can I change plans later?
            </summary>
            <p className="text-slate-300 mt-3">
              Yes! You can upgrade or downgrade your plan anytime. Changes take effect on your next billing cycle.
            </p>
          </details>

          <details className="bg-slate-800 p-6 rounded-lg cursor-pointer">
            <summary className="text-lg font-semibold text-white">
              How do I cancel my subscription?
            </summary>
            <p className="text-slate-300 mt-3">
              You can cancel anytime from your account settings. Your access continues until the end of the billing period.
            </p>
          </details>

          <details className="bg-slate-800 p-6 rounded-lg cursor-pointer">
            <summary className="text-lg font-semibold text-white">
              Is there a free trial for paid plans?
            </summary>
            <p className="text-slate-300 mt-3">
              We offer a Free tier with full access to core features. Upgrade to Pro or Team whenever you need premium features.
            </p>
          </details>

          <details className="bg-slate-800 p-6 rounded-lg cursor-pointer">
            <summary className="text-lg font-semibold text-white">
              What payment methods do you accept?
            </summary>
            <p className="text-slate-300 mt-3">
              We accept all major credit and debit cards through Razorpay. UPI, netbanking, and wallets are also supported.
            </p>
          </details>
        </div>
      </div>

      {/* Razorpay Script - Load once on component mount */}
      <script
        src="https://checkout.razorpay.com/v1/checkout.js"
        async
      />
    </div>
  );
}

// Type declaration for window.Razorpay
declare global {
  interface Window {
    Razorpay: any;
  }
}
