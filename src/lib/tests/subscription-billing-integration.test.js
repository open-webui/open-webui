/**
 * Integration tests for subscription billing functionality
 * Tests the complete workflow from API to UI component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import MyOrganizationUsage from '$lib/components/admin/Settings/MyOrganizationUsage.svelte';
import { getSubscriptionBilling } from '$lib/apis/organizations';

// Mock the API function
vi.mock('$lib/apis/organizations', () => ({
    getSubscriptionBilling: vi.fn(),
    getClientUsageSummary: vi.fn(),
    getTodayUsage: vi.fn(),
    getBillingSummary: vi.fn(),
    getUsageByUser: vi.fn(),
    getUsageByModel: vi.fn()
}));

// Mock user store
vi.mock('$lib/stores', () => ({
    user: {
        subscribe: vi.fn((callback) => {
            callback({
                id: 'admin_123',
                name: 'Admin User',
                email: 'admin@test.com',
                role: 'admin',
                profile_image_url: '/user.png'
            });
            return () => {};
        })
    }
}));

// Mock toast
vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

describe('Subscription Billing Integration Tests', () => {
    const mockSubscriptionData = {
        success: true,
        client_id: 'org_123',
        client_name: 'Test Organization',
        subscription_data: {
            current_month: {
                month: 1,
                year: 2024,
                days_in_month: 31,
                total_users: 5,
                current_tier_price_pln: 69,
                total_cost_pln: 285.55,
                tier_breakdown: [
                    {
                        tier_range: '1-3 users',
                        price_per_user_pln: 79,
                        is_current_tier: false,
                        user_count_in_tier: 0
                    },
                    {
                        tier_range: '4-9 users',
                        price_per_user_pln: 69,
                        is_current_tier: true,
                        user_count_in_tier: 5
                    },
                    {
                        tier_range: '10-19 users',
                        price_per_user_pln: 59,
                        is_current_tier: false,
                        user_count_in_tier: 0
                    },
                    {
                        tier_range: '20+ users',
                        price_per_user_pln: 54,
                        is_current_tier: false,
                        user_count_in_tier: 0
                    }
                ],
                user_details: [
                    {
                        user_id: 'user_1',
                        user_name: 'User One',
                        user_email: 'user1@test.com',
                        created_at: 1704067200,
                        created_date: '2024-01-01',
                        days_remaining_when_added: 31,
                        billing_proportion: 1.0,
                        monthly_cost_pln: 69.0
                    },
                    {
                        user_id: 'user_2',
                        user_name: 'User Two',
                        user_email: 'user2@test.com',
                        created_at: 1705276800,
                        created_date: '2024-01-15',
                        days_remaining_when_added: 17,
                        billing_proportion: 0.548,
                        monthly_cost_pln: 37.81
                    },
                    {
                        user_id: 'user_3',
                        user_name: 'User Three',
                        user_email: 'user3@test.com',
                        created_at: 1706140800,
                        created_date: '2024-01-25',
                        days_remaining_when_added: 7,
                        billing_proportion: 0.226,
                        monthly_cost_pln: 15.59
                    },
                    {
                        user_id: 'user_4',
                        user_name: 'User Four',
                        user_email: 'user4@test.com',
                        created_at: 1706659200,
                        created_date: '2024-01-31',
                        days_remaining_when_added: 1,
                        billing_proportion: 0.032,
                        monthly_cost_pln: 2.21
                    },
                    {
                        user_id: 'user_5',
                        user_name: 'User Five',
                        user_email: 'user5@test.com',
                        created_at: 1704412800,
                        created_date: '2024-01-05',
                        days_remaining_when_added: 27,
                        billing_proportion: 0.871,
                        monthly_cost_pln: 60.09
                    }
                ]
            },
            pricing_tiers: [
                { range: '1-3 users', price_pln: 79 },
                { range: '4-9 users', price_pln: 69 },
                { range: '10-19 users', price_pln: 59 },
                { range: '20+ users', price_pln: 54 }
            ]
        }
    };

    beforeEach(() => {
        vi.clearAllMocks();
        
        // Mock all the API functions with default responses
        getSubscriptionBilling.mockResolvedValue(mockSubscriptionData);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should render subscription tab and load data successfully', async () => {
        render(MyOrganizationUsage);

        // Wait for component to mount and check for Subscription tab
        await waitFor(() => {
            expect(screen.getByText('Subscription')).toBeInTheDocument();
        });

        // Click on Subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for subscription data to load
        await waitFor(() => {
            expect(getSubscriptionBilling).toHaveBeenCalledWith(undefined, undefined);
        });

        // Check that subscription content is displayed
        await waitFor(() => {
            expect(screen.getByText('Current Month Billing')).toBeInTheDocument();
            expect(screen.getByText('5 Users')).toBeInTheDocument();
            expect(screen.getByText('285.55 PLN')).toBeInTheDocument();
            expect(screen.getByText('4-9 users tier')).toBeInTheDocument();
        });
    });

    it('should display pricing tiers correctly', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for data to load and check pricing tiers
        await waitFor(() => {
            expect(screen.getByText('Pricing Tiers')).toBeInTheDocument();
        });

        // Check all pricing tiers are displayed
        await waitFor(() => {
            expect(screen.getByText('1-3 users: 79 PLN')).toBeInTheDocument();
            expect(screen.getByText('4-9 users: 69 PLN')).toBeInTheDocument();
            expect(screen.getByText('10-19 users: 59 PLN')).toBeInTheDocument();
            expect(screen.getByText('20+ users: 54 PLN')).toBeInTheDocument();
        });

        // Check current tier is highlighted
        const currentTierCard = screen.getByText('4-9 users: 69 PLN').closest('[class*="border"]');
        expect(currentTierCard).toHaveClass('border-primary-500');
    });

    it('should display user details table with correct data', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for user details table
        await waitFor(() => {
            expect(screen.getByText('User Details')).toBeInTheDocument();
        });

        // Check table headers
        await waitFor(() => {
            expect(screen.getByText('User')).toBeInTheDocument();
            expect(screen.getByText('Added Date')).toBeInTheDocument();
            expect(screen.getByText('Billing %')).toBeInTheDocument();
            expect(screen.getByText('Monthly Cost')).toBeInTheDocument();
        });

        // Check user data is displayed
        await waitFor(() => {
            expect(screen.getByText('User One')).toBeInTheDocument();
            expect(screen.getByText('user1@test.com')).toBeInTheDocument();
            expect(screen.getByText('2024-01-01')).toBeInTheDocument();
            expect(screen.getByText('100.0%')).toBeInTheDocument();
            expect(screen.getByText('69.00 PLN')).toBeInTheDocument();
        });

        // Check proportional billing for mid-month user
        await waitFor(() => {
            expect(screen.getByText('User Two')).toBeInTheDocument();
            expect(screen.getByText('54.8%')).toBeInTheDocument();
            expect(screen.getByText('37.81 PLN')).toBeInTheDocument();
        });
    });

    it('should handle API errors gracefully', async () => {
        // Mock API to return error
        getSubscriptionBilling.mockRejectedValue(new Error('API Error'));

        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for error state
        await waitFor(() => {
            expect(screen.getByText('Error loading subscription data')).toBeInTheDocument();
        });
    });

    it('should handle empty organization (no users)', async () => {
        // Mock empty organization response
        const emptyOrgData = {
            ...mockSubscriptionData,
            subscription_data: {
                ...mockSubscriptionData.subscription_data,
                current_month: {
                    ...mockSubscriptionData.subscription_data.current_month,
                    total_users: 0,
                    total_cost_pln: 0.0,
                    user_details: []
                }
            }
        };

        getSubscriptionBilling.mockResolvedValue(emptyOrgData);

        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for data and check empty state
        await waitFor(() => {
            expect(screen.getByText('0 Users')).toBeInTheDocument();
            expect(screen.getByText('0.00 PLN')).toBeInTheDocument();
            expect(screen.getByText('No users in organization')).toBeInTheDocument();
        });
    });

    it('should refresh data when refresh button is clicked', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for initial load
        await waitFor(() => {
            expect(getSubscriptionBilling).toHaveBeenCalledTimes(1);
        });

        // Click refresh button
        const refreshButton = screen.getByLabelText('Refresh subscription data');
        await fireEvent.click(refreshButton);

        // Verify API was called again
        await waitFor(() => {
            expect(getSubscriptionBilling).toHaveBeenCalledTimes(2);
        });
    });

    it('should display loading state while fetching data', async () => {
        // Mock API to return a promise that doesn't resolve immediately
        let resolvePromise;
        const promise = new Promise(resolve => {
            resolvePromise = resolve;
        });
        getSubscriptionBilling.mockReturnValue(promise);

        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Check loading state
        await waitFor(() => {
            expect(screen.getByText('Loading subscription data...')).toBeInTheDocument();
        });

        // Resolve the promise
        resolvePromise(mockSubscriptionData);

        // Wait for loading to complete
        await waitFor(() => {
            expect(screen.queryByText('Loading subscription data...')).not.toBeInTheDocument();
            expect(screen.getByText('Current Month Billing')).toBeInTheDocument();
        });
    });

    it('should calculate and display tier breakdown correctly', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for tier breakdown section
        await waitFor(() => {
            expect(screen.getByText('Tier Breakdown')).toBeInTheDocument();
        });

        // Check current tier is highlighted and shows user count
        await waitFor(() => {
            const currentTierElement = screen.getByText('4-9 users').closest('[class*="border"]');
            expect(currentTierElement).toHaveClass('border-primary-500');
            expect(screen.getByText('5 users in this tier')).toBeInTheDocument();
        });

        // Check non-current tiers are properly styled
        const tier1Element = screen.getByText('1-3 users').closest('[class*="border"]');
        expect(tier1Element).toHaveClass('border-gray-200');
    });

    it('should format currency and percentages correctly', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for data to load
        await waitFor(() => {
            // Check PLN currency formatting
            expect(screen.getByText('285.55 PLN')).toBeInTheDocument();
            expect(screen.getByText('69.00 PLN')).toBeInTheDocument();
            expect(screen.getByText('37.81 PLN')).toBeInTheDocument();

            // Check percentage formatting
            expect(screen.getByText('100.0%')).toBeInTheDocument();
            expect(screen.getByText('54.8%')).toBeInTheDocument();
            expect(screen.getByText('22.6%')).toBeInTheDocument();
        });
    });

    it('should sort user details by addition date (newest first)', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for user details table
        await waitFor(() => {
            expect(screen.getByText('User Details')).toBeInTheDocument();
        });

        // Get all user name elements in the table
        const userRows = screen.getAllByText(/User (One|Two|Three|Four|Five)/);
        
        // Check that users are sorted by creation date (newest first)
        // User Four (2024-01-31) should be first, User One (2024-01-01) should be last
        expect(userRows[0]).toHaveTextContent('User Four');
        expect(userRows[userRows.length - 1]).toHaveTextContent('User One');
    });

    it('should handle non-admin users correctly', async () => {
        // Mock non-admin user
        vi.mocked(user.subscribe).mockImplementation((callback) => {
            callback({
                id: 'user_123',
                name: 'Regular User',
                email: 'user@test.com',
                role: 'user',
                profile_image_url: '/user.png'
            });
            return () => {};
        });

        render(MyOrganizationUsage);

        // Non-admin users should not see subscription tab
        await waitFor(() => {
            expect(screen.queryByText('Subscription')).not.toBeInTheDocument();
        });
    });
});

describe('Subscription Billing Data Transformation', () => {
    it('should correctly calculate total costs', () => {
        const userDetails = mockSubscriptionData.subscription_data.current_month.user_details;
        const totalCost = userDetails.reduce((sum, user) => sum + user.monthly_cost_pln, 0);
        
        expect(Math.round(totalCost * 100) / 100).toBe(184.7);
    });

    it('should validate billing proportion calculations', () => {
        const userDetails = mockSubscriptionData.subscription_data.current_month.user_details;
        
        userDetails.forEach(user => {
            expect(user.billing_proportion).toBeGreaterThanOrEqual(0);
            expect(user.billing_proportion).toBeLessThanOrEqual(1);
            
            // Verify cost calculation: cost = tier_price * proportion
            const expectedCost = Math.round(69 * user.billing_proportion * 100) / 100;
            expect(user.monthly_cost_pln).toBe(expectedCost);
        });
    });

    it('should verify tier assignment logic', () => {
        const totalUsers = mockSubscriptionData.subscription_data.current_month.total_users;
        const currentTierPrice = mockSubscriptionData.subscription_data.current_month.current_tier_price_pln;
        
        // 5 users should be in 4-9 users tier (69 PLN)
        expect(totalUsers).toBe(5);
        expect(currentTierPrice).toBe(69);
        
        // Verify tier breakdown reflects this
        const tierBreakdown = mockSubscriptionData.subscription_data.current_month.tier_breakdown;
        const currentTier = tierBreakdown.find(tier => tier.is_current_tier);
        
        expect(currentTier.tier_range).toBe('4-9 users');
        expect(currentTier.price_per_user_pln).toBe(69);
        expect(currentTier.user_count_in_tier).toBe(5);
    });
});

describe('Subscription Billing Performance Tests', () => {
    it('should handle large user datasets efficiently', async () => {
        // Create mock data with 100 users
        const largeUserData = {
            ...mockSubscriptionData,
            subscription_data: {
                ...mockSubscriptionData.subscription_data,
                current_month: {
                    ...mockSubscriptionData.subscription_data.current_month,
                    total_users: 100,
                    current_tier_price_pln: 54, // 20+ users tier
                    user_details: Array.from({ length: 100 }, (_, i) => ({
                        user_id: `user_${i}`,
                        user_name: `User ${i}`,
                        user_email: `user${i}@test.com`,
                        created_at: Date.now() - (i * 86400000),
                        created_date: new Date(Date.now() - (i * 86400000)).toISOString().split('T')[0],
                        days_remaining_when_added: 30 - (i % 30),
                        billing_proportion: (30 - (i % 30)) / 30,
                        monthly_cost_pln: 54 * ((30 - (i % 30)) / 30)
                    }))
                }
            }
        };

        getSubscriptionBilling.mockResolvedValue(largeUserData);

        const startTime = performance.now();
        
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for data to load
        await waitFor(() => {
            expect(screen.getByText('100 Users')).toBeInTheDocument();
        });

        const endTime = performance.now();
        const renderTime = endTime - startTime;

        // Should render in reasonable time (less than 1 second)
        expect(renderTime).toBeLessThan(1000);
    });

    it('should efficiently update when data changes', async () => {
        render(MyOrganizationUsage);

        // Navigate to subscription tab
        const subscriptionTab = screen.getByText('Subscription');
        await fireEvent.click(subscriptionTab);

        // Wait for initial data
        await waitFor(() => {
            expect(screen.getByText('5 Users')).toBeInTheDocument();
        });

        // Update mock data
        const updatedData = {
            ...mockSubscriptionData,
            subscription_data: {
                ...mockSubscriptionData.subscription_data,
                current_month: {
                    ...mockSubscriptionData.subscription_data.current_month,
                    total_users: 6,
                    total_cost_pln: 350.55
                }
            }
        };

        getSubscriptionBilling.mockResolvedValue(updatedData);

        const startTime = performance.now();

        // Trigger refresh
        const refreshButton = screen.getByLabelText('Refresh subscription data');
        await fireEvent.click(refreshButton);

        // Wait for updated data
        await waitFor(() => {
            expect(screen.getByText('6 Users')).toBeInTheDocument();
        });

        const endTime = performance.now();
        const updateTime = endTime - startTime;

        // Update should be fast (less than 500ms)
        expect(updateTime).toBeLessThan(500);
    });
});