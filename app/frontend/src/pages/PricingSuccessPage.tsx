/**
 * Pricing Success Page
 * Shown after user successfully completes payment
 */

import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getSubscriptionStatus } from '../services/paymentService';

export function PricingSuccessPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const planUpgradedTo = (location.state as any)?.plan || 'pro';

  useEffect(() => {
    // Fetch subscription status to confirm payment was processed
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const status = await getSubscriptionStatus();
        setSubscription(status);
      } catch (error) {
        console.error('Failed to fetch subscription status:', error);
      } finally {
        setLoading(false);
      }
    };

    // Give webhook a moment to process (up to 5 seconds)
    const timer = setTimeout(fetchStatus, 1000);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin">
            <svg
              className="w-12 h-12 text-blue-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
              />
            </svg>
          </div>
          <p className="mt-4 text-slate-300">Confirming your payment...</p>
        </div>
      </div>
    );
  }

  const isSubscriptionActive = subscription?.status === 'active';
  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        {/* Success Card */}
        <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-2xl p-12 text-center">
          {/* Success Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center">
              <svg
                className="w-10 h-10 text-green-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-bold text-white mb-2">
            Payment Successful! 🎉
          </h1>
          <p className="text-slate-300 mb-8">
            Your subscription has been activated
          </p>

          {/* Subscription Details */}
          <div className="bg-slate-800/50 rounded-lg p-6 mb-8 text-left">
            <h2 className="text-lg font-semibold text-white mb-4">
              Subscription Details
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center pb-3 border-b border-slate-700">
                <span className="text-slate-300">Plan</span>
                <span className="font-semibold text-white capitalize">
                  {subscription?.plan || planUpgradedTo}
                </span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-700">
                <span className="text-slate-300">Status</span>
                <span
                  className={`font-semibold ${
                    isSubscriptionActive
                      ? 'text-green-400'
                      : 'text-yellow-400'
                  }`}
                >
                  {subscription?.status === 'active' ? (
                    <>
                      <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
                      Active
                    </>
                  ) : (
                    'Processing'
                  )}
                </span>
              </div>
              {periodEnd && isSubscriptionActive && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Renews On</span>
                  <span className="font-semibold text-white">{periodEnd}</span>
                </div>
              )}
            </div>
          </div>

          {/* What's Included */}
          {subscription?.plan === 'pro' && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-6 mb-8 text-left">
              <h3 className="font-semibold text-white mb-4">
                ✨ You now have access to:
              </h3>
              <ul className="space-y-2 text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Share chat sessions
                  (up to 5)
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Priority support
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Unlimited
                  repositories
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Advanced analytics
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> API access
                </li>
              </ul>
            </div>
          )}

          {subscription?.plan === 'team' && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-6 mb-8 text-left">
              <h3 className="font-semibold text-white mb-4">
                ✨ You now have access to:
              </h3>
              <ul className="space-y-2 text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Share chat sessions
                  (up to 20)
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Team management
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Team analytics
                  dashboard
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Dedicated support
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Custom integrations
                </li>
              </ul>
            </div>
          )}

          {/* Next Steps */}
          <div className="bg-slate-800/30 rounded-lg p-6 mb-8">
            <h3 className="font-semibold text-white mb-3">What's next?</h3>
            <ol className="text-left text-slate-300 space-y-2">
              <li>1. Return to InfraLens and start using premium features</li>
              <li>2. You'll receive a confirmation email shortly</li>
              <li>3. Your subscription will auto-renew on {periodEnd}</li>
              <li>4. Manage billing in your account settings anytime</li>
            </ol>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={() => navigate('/chat')}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Go to Dashboard
            </button>
            <button
              onClick={() => navigate('/pricing')}
              className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Manage Subscription
            </button>
          </div>
        </div>

        {/* Support Notice */}
        <div className="mt-8 text-center text-slate-400">
          <p className="mb-2">Questions? We're here to help</p>
          <p>Email us at support@infralens.dev</p>
        </div>
      </div>
    </div>
  );
}
