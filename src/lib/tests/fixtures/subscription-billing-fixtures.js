/**
 * Test fixtures and mock data for subscription billing tests
 * Provides realistic test scenarios for comprehensive testing
 */

/**
 * Base organization fixture
 */
export const baseOrganization = {
    id: 'org_test_123',
    name: 'Test Organization',
    markup_rate: 1.3,
    monthly_limit: 1000.0,
    billing_email: 'billing@test.com',
    is_active: true,
    created_at: 1704067200, // 2024-01-01
    updated_at: 1704067200
};

/**
 * Admin user fixture
 */
export const adminUser = {
    id: 'admin_test_123',
    name: 'Test Admin',
    email: 'admin@test.com',
    role: 'admin',
    profile_image_url: '/user.png',
    last_active_at: Math.floor(Date.now() / 1000),
    created_at: 1704067200,
    updated_at: Math.floor(Date.now() / 1000)
};

/**
 * Regular user fixture
 */
export const regularUser = {
    id: 'user_test_123',
    name: 'Test User',
    email: 'user@test.com',
    role: 'user',
    profile_image_url: '/user.png',
    last_active_at: Math.floor(Date.now() / 1000),
    created_at: 1704067200,
    updated_at: Math.floor(Date.now() / 1000)
};

/**
 * Small organization scenario (1-3 users tier)
 */
export const smallOrgSubscription = {
    success: true,
    client_id: 'org_small_123',
    client_name: 'Small Organization',
    subscription_data: {
        current_month: {
            month: 1,
            year: 2024,
            days_in_month: 31,
            total_users: 2,
            current_tier_price_pln: 79,
            total_cost_pln: 142.26,
            tier_breakdown: [
                {
                    tier_range: '1-3 users',
                    price_per_user_pln: 79,
                    is_current_tier: true,
                    user_count_in_tier: 2
                },
                {
                    tier_range: '4-9 users',
                    price_per_user_pln: 69,
                    is_current_tier: false,
                    user_count_in_tier: 0
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
                    user_id: 'user_small_1',
                    user_name: 'Small Org Admin',
                    user_email: 'admin@small.com',
                    created_at: 1704067200, // 2024-01-01
                    created_date: '2024-01-01',
                    days_remaining_when_added: 31,
                    billing_proportion: 1.0,
                    monthly_cost_pln: 79.0
                },
                {
                    user_id: 'user_small_2',
                    user_name: 'Small Org User',
                    user_email: 'user@small.com',
                    created_at: 1705708800, // 2024-01-20
                    created_date: '2024-01-20',
                    days_remaining_when_added: 12,
                    billing_proportion: 0.387,
                    monthly_cost_pln: 30.58
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

/**
 * Medium organization scenario (4-9 users tier)
 */
export const mediumOrgSubscription = {
    success: true,
    client_id: 'org_medium_123',
    client_name: 'Medium Organization',
    subscription_data: {
        current_month: {
            month: 1,
            year: 2024,
            days_in_month: 31,
            total_users: 7,
            current_tier_price_pln: 69,
            total_cost_pln: 398.42,
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
                    user_count_in_tier: 7
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
                    user_id: 'user_med_1',
                    user_name: 'Medium Admin',
                    user_email: 'admin@medium.com',
                    created_at: 1704067200, // 2024-01-01
                    created_date: '2024-01-01',
                    days_remaining_when_added: 31,
                    billing_proportion: 1.0,
                    monthly_cost_pln: 69.0
                },
                {
                    user_id: 'user_med_2',
                    user_name: 'User Two',
                    user_email: 'user2@medium.com',
                    created_at: 1704326400, // 2024-01-04
                    created_date: '2024-01-04',
                    days_remaining_when_added: 28,
                    billing_proportion: 0.903,
                    monthly_cost_pln: 62.31
                },
                {
                    user_id: 'user_med_3',
                    user_name: 'User Three',
                    user_email: 'user3@medium.com',
                    created_at: 1704758400, // 2024-01-09
                    created_date: '2024-01-09',
                    days_remaining_when_added: 23,
                    billing_proportion: 0.742,
                    monthly_cost_pln: 51.19
                },
                {
                    user_id: 'user_med_4',
                    user_name: 'User Four',
                    user_email: 'user4@medium.com',
                    created_at: 1705276800, // 2024-01-15
                    created_date: '2024-01-15',
                    days_remaining_when_added: 17,
                    billing_proportion: 0.548,
                    monthly_cost_pln: 37.81
                },
                {
                    user_id: 'user_med_5',
                    user_name: 'User Five',
                    user_email: 'user5@medium.com',
                    created_at: 1705795200, // 2024-01-21
                    created_date: '2024-01-21',
                    days_remaining_when_added: 11,
                    billing_proportion: 0.355,
                    monthly_cost_pln: 24.48
                },
                {
                    user_id: 'user_med_6',
                    user_name: 'User Six',
                    user_email: 'user6@medium.com',
                    created_at: 1706313600, // 2024-01-27
                    created_date: '2024-01-27',
                    days_remaining_when_added: 5,
                    billing_proportion: 0.161,
                    monthly_cost_pln: 11.11
                },
                {
                    user_id: 'user_med_7',
                    user_name: 'User Seven',
                    user_email: 'user7@medium.com',
                    created_at: 1706659200, // 2024-01-31
                    created_date: '2024-01-31',
                    days_remaining_when_added: 1,
                    billing_proportion: 0.032,
                    monthly_cost_pln: 2.21
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

/**
 * Large organization scenario (10-19 users tier)
 */
export const largeOrgSubscription = {
    success: true,
    client_id: 'org_large_123',
    client_name: 'Large Organization',
    subscription_data: {
        current_month: {
            month: 1,
            year: 2024,
            days_in_month: 31,
            total_users: 15,
            current_tier_price_pln: 59,
            total_cost_pln: 708.75,
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
                    is_current_tier: false,
                    user_count_in_tier: 0
                },
                {
                    tier_range: '10-19 users',
                    price_per_user_pln: 59,
                    is_current_tier: true,
                    user_count_in_tier: 15
                },
                {
                    tier_range: '20+ users',
                    price_per_user_pln: 54,
                    is_current_tier: false,
                    user_count_in_tier: 0
                }
            ],
            user_details: generateUserDetails(15, 59, 'large', 1704067200)
        },
        pricing_tiers: [
            { range: '1-3 users', price_pln: 79 },
            { range: '4-9 users', price_pln: 69 },
            { range: '10-19 users', price_pln: 59 },
            { range: '20+ users', price_pln: 54 }
        ]
    }
};

/**
 * Enterprise organization scenario (20+ users tier)
 */
export const enterpriseOrgSubscription = {
    success: true,
    client_id: 'org_enterprise_123',
    client_name: 'Enterprise Organization',
    subscription_data: {
        current_month: {
            month: 1,
            year: 2024,
            days_in_month: 31,
            total_users: 25,
            current_tier_price_pln: 54,
            total_cost_pln: 1080.0,
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
                    is_current_tier: false,
                    user_count_in_tier: 0
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
                    is_current_tier: true,
                    user_count_in_tier: 25
                }
            ],
            user_details: generateUserDetails(25, 54, 'enterprise', 1704067200)
        },
        pricing_tiers: [
            { range: '1-3 users', price_pln: 79 },
            { range: '4-9 users', price_pln: 69 },
            { range: '10-19 users', price_pln: 59 },
            { range: '20+ users', price_pln: 54 }
        ]
    }
};

/**
 * Empty organization scenario (no users)
 */
export const emptyOrgSubscription = {
    success: true,
    client_id: 'org_empty_123',
    client_name: 'Empty Organization',
    subscription_data: {
        current_month: {
            month: 1,
            year: 2024,
            days_in_month: 31,
            total_users: 0,
            current_tier_price_pln: 0,
            total_cost_pln: 0.0,
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
                    is_current_tier: false,
                    user_count_in_tier: 0
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
            user_details: []
        },
        pricing_tiers: [
            { range: '1-3 users', price_pln: 79 },
            { range: '4-9 users', price_pln: 69 },
            { range: '10-19 users', price_pln: 59 },
            { range: '20+ users', price_pln: 54 }
        ]
    }
};

/**
 * Leap year February scenario (29 days)
 */
export const leapYearFebruarySubscription = {
    success: true,
    client_id: 'org_leap_123',
    client_name: 'Leap Year Organization',
    subscription_data: {
        current_month: {
            month: 2,
            year: 2024, // Leap year
            days_in_month: 29,
            total_users: 3,
            current_tier_price_pln: 79,
            total_cost_pln: 189.34,
            tier_breakdown: [
                {
                    tier_range: '1-3 users',
                    price_per_user_pln: 79,
                    is_current_tier: true,
                    user_count_in_tier: 3
                },
                {
                    tier_range: '4-9 users',
                    price_per_user_pln: 69,
                    is_current_tier: false,
                    user_count_in_tier: 0
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
                    user_id: 'user_leap_1',
                    user_name: 'Leap Admin',
                    user_email: 'admin@leap.com',
                    created_at: 1706745600, // 2024-02-01
                    created_date: '2024-02-01',
                    days_remaining_when_added: 29,
                    billing_proportion: 1.0,
                    monthly_cost_pln: 79.0
                },
                {
                    user_id: 'user_leap_2',
                    user_name: 'Mid Month User',
                    user_email: 'mid@leap.com',
                    created_at: 1707955200, // 2024-02-15
                    created_date: '2024-02-15',
                    days_remaining_when_added: 15,
                    billing_proportion: 0.517,
                    monthly_cost_pln: 40.84
                },
                {
                    user_id: 'user_leap_3',
                    user_name: 'Leap Day User',
                    user_email: 'leap@leap.com',
                    created_at: 1709164800, // 2024-02-29
                    created_date: '2024-02-29',
                    days_remaining_when_added: 1,
                    billing_proportion: 0.034,
                    monthly_cost_pln: 2.69
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

/**
 * Error response scenarios
 */
export const errorResponses = {
    unauthorized: {
        status: 403,
        detail: 'Admin access required'
    },
    notFound: {
        status: 404,
        detail: 'Organization not found'
    },
    serverError: {
        status: 500,
        detail: 'Internal server error'
    },
    networkError: new Error('Network connection failed'),
    invalidData: {
        status: 422,
        detail: 'Invalid client_id format'
    }
};

/**
 * Helper function to generate user details for large organizations
 */
function generateUserDetails(userCount, tierPrice, orgPrefix, baseTimestamp) {
    const details = [];
    const daysInMonth = 31;
    
    for (let i = 0; i < userCount; i++) {
        const dayAdded = Math.floor(Math.random() * daysInMonth) + 1;
        const createdTimestamp = baseTimestamp + (dayAdded - 1) * 86400; // Add days in seconds
        const daysRemaining = daysInMonth - dayAdded + 1;
        const proportion = daysRemaining / daysInMonth;
        const monthlyCost = Math.round(tierPrice * proportion * 100) / 100;
        
        details.push({
            user_id: `user_${orgPrefix}_${i + 1}`,
            user_name: `${orgPrefix.charAt(0).toUpperCase() + orgPrefix.slice(1)} User ${i + 1}`,
            user_email: `user${i + 1}@${orgPrefix}.com`,
            created_at: createdTimestamp,
            created_date: new Date(createdTimestamp * 1000).toISOString().split('T')[0],
            days_remaining_when_added: daysRemaining,
            billing_proportion: Math.round(proportion * 1000) / 1000,
            monthly_cost_pln: monthlyCost
        });
    }
    
    // Sort by creation date (newest first)
    return details.sort((a, b) => b.created_at - a.created_at);
}

/**
 * Mock API response factory
 */
export const createMockResponse = (data, status = 200, delay = 0) => {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (status >= 400) {
                reject(data);
            } else {
                resolve(data);
            }
        }, delay);
    });
};

/**
 * Test scenario configurations
 */
export const testScenarios = {
    small: {
        name: 'Small Organization (1-3 users)',
        data: smallOrgSubscription,
        expectedTier: '1-3 users',
        expectedPrice: 79
    },
    medium: {
        name: 'Medium Organization (4-9 users)',
        data: mediumOrgSubscription,
        expectedTier: '4-9 users',
        expectedPrice: 69
    },
    large: {
        name: 'Large Organization (10-19 users)',
        data: largeOrgSubscription,
        expectedTier: '10-19 users',
        expectedPrice: 59
    },
    enterprise: {
        name: 'Enterprise Organization (20+ users)',
        data: enterpriseOrgSubscription,
        expectedTier: '20+ users',
        expectedPrice: 54
    },
    empty: {
        name: 'Empty Organization (0 users)',
        data: emptyOrgSubscription,
        expectedTier: null,
        expectedPrice: 0
    },
    leapYear: {
        name: 'Leap Year February',
        data: leapYearFebruarySubscription,
        expectedTier: '1-3 users',
        expectedPrice: 79
    }
};

/**
 * Database model fixtures for backend tests
 */
export const dbFixtures = {
    organizations: [
        baseOrganization,
        { ...baseOrganization, id: 'org_small_123', name: 'Small Organization' },
        { ...baseOrganization, id: 'org_medium_123', name: 'Medium Organization' },
        { ...baseOrganization, id: 'org_large_123', name: 'Large Organization' },
        { ...baseOrganization, id: 'org_enterprise_123', name: 'Enterprise Organization' }
    ],
    users: [
        adminUser,
        regularUser,
        { ...regularUser, id: 'user_small_1', email: 'admin@small.com' },
        { ...regularUser, id: 'user_small_2', email: 'user@small.com' }
    ],
    userMappings: [
        {
            id: 'mapping_1',
            user_id: 'user_small_1',
            client_org_id: 'org_small_123',
            openrouter_user_id: 'openrouter_user_1',
            is_active: true,
            created_at: 1704067200,
            updated_at: 1704067200
        },
        {
            id: 'mapping_2',
            user_id: 'user_small_2',
            client_org_id: 'org_small_123',
            openrouter_user_id: 'openrouter_user_2',
            is_active: true,
            created_at: 1705708800,
            updated_at: 1705708800
        }
    ]
};