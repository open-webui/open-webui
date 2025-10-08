<script lang="ts">
  import { onMount } from 'svelte';
  import { selectionsAPI, type Selection, type SelectionStats } from '$lib/apis/selections';
  import { user } from '$lib/stores';
  import { get } from 'svelte/store';

  let stats: SelectionStats | null = null;
  let analytics: Selection[] = [];
  let loading = false;
  let error = '';
  let selectedRole: string = '';
  let dateRange = { start: '', end: '' };

  // Check if user is admin
  $: isAdmin = $user?.role === 'admin';

  onMount(() => {
    if (isAdmin) {
      loadStats();
      loadAnalytics();
    }
  });

  async function loadStats() {
    try {
      loading = true;
      stats = await selectionsAPI.getSelectionStats();
    } catch (err) {
      error = `Failed to load stats: ${err}`;
    } finally {
      loading = false;
    }
  }

  async function loadAnalytics() {
    try {
      loading = true;
      const startDate = dateRange.start ? new Date(dateRange.start).getTime() * 1000000 : undefined;
      const endDate = dateRange.end ? new Date(dateRange.end).getTime() * 1000000 : undefined;
      
      analytics = await selectionsAPI.getAnalyticsData(
        startDate,
        endDate,
        selectedRole || undefined,
        1000
      );
    } catch (err) {
      error = `Failed to load analytics: ${err}`;
    } finally {
      loading = false;
    }
  }

  function exportToCSV() {
    if (analytics.length === 0) return;

    const headers = ['ID', 'User ID', 'Chat ID', 'Message ID', 'Role', 'Selected Text', 'Context', 'Created At'];
    const csvContent = [
      headers.join(','),
      ...analytics.map(selection => [
        selection.id,
        selection.user_id,
        selection.chat_id,
        selection.message_id,
        selection.role,
        `"${selection.selected_text.replace(/"/g, '""')}"`, // Escape quotes
        `"${(selection.context || '').replace(/"/g, '""')}"`,
        new Date(selection.created_at / 1000000).toISOString()
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `selections-analytics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function formatDate(timestamp: number): string {
    return new Date(timestamp / 1000000).toLocaleString();
  }

  function truncateText(text: string, maxLength: number = 100): string {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }
</script>

{#if !isAdmin}
  <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
    <h3 class="text-red-800 font-semibold">Access Denied</h3>
    <p class="text-red-600">Admin access required to view selection analytics.</p>
  </div>
{:else}
  <div class="p-6 space-y-6">
    <div class="flex justify-between items-center">
      <h2 class="text-2xl font-bold text-gray-900">Selection Analytics</h2>
      <button
        on:click={exportToCSV}
        disabled={analytics.length === 0}
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Export CSV
      </button>
    </div>

    {#if error}
      <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-600">{error}</p>
      </div>
    {/if}

    <!-- Stats Cards -->
    {#if stats}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 rounded-lg shadow">
          <h3 class="text-sm font-medium text-gray-500">Total Selections</h3>
          <p class="text-2xl font-bold text-gray-900">{stats.total_selections}</p>
        </div>
        <div class="bg-white p-4 rounded-lg shadow">
          <h3 class="text-sm font-medium text-gray-500">Unique Users</h3>
          <p class="text-2xl font-bold text-gray-900">{stats.unique_users}</p>
        </div>
        <div class="bg-white p-4 rounded-lg shadow">
          <h3 class="text-sm font-medium text-gray-500">Assistant Selections</h3>
          <p class="text-2xl font-bold text-gray-900">{stats.assistant_selections}</p>
        </div>
        <div class="bg-white p-4 rounded-lg shadow">
          <h3 class="text-sm font-medium text-gray-500">User Selections</h3>
          <p class="text-2xl font-bold text-gray-900">{stats.user_selections}</p>
        </div>
      </div>
    {/if}

    <!-- Filters -->
    <div class="bg-white p-4 rounded-lg shadow">
      <h3 class="text-lg font-semibold mb-4">Filters</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label for="role" class="block text-sm font-medium text-gray-700">Role</label>
          <select
            id="role"
            bind:value={selectedRole}
            on:change={loadAnalytics}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">All Roles</option>
            <option value="user">User</option>
            <option value="assistant">Assistant</option>
          </select>
        </div>
        <div>
          <label for="startDate" class="block text-sm font-medium text-gray-700">Start Date</label>
          <input
            id="startDate"
            type="date"
            bind:value={dateRange.start}
            on:change={loadAnalytics}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
        <div>
          <label for="endDate" class="block text-sm font-medium text-gray-700">End Date</label>
          <input
            id="endDate"
            type="date"
            bind:value={dateRange.end}
            on:change={loadAnalytics}
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>

    <!-- Analytics Table -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200">
        <h3 class="text-lg font-semibold">Selection Data ({analytics.length} records)</h3>
      </div>
      
      {#if loading}
        <div class="p-8 text-center">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p class="mt-2 text-gray-600">Loading analytics data...</p>
        </div>
      {:else if analytics.length === 0}
        <div class="p-8 text-center text-gray-500">
          <p>No selection data found for the selected filters.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User ID
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Chat ID
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Selected Text
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Context
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created At
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each analytics as selection}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {selection.user_id}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {selection.chat_id}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full {selection.role === 'user' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}">
                      {selection.role}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    <div class="truncate" title={selection.selected_text}>
                      {truncateText(selection.selected_text, 50)}
                    </div>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    {#if selection.context}
                      <div class="truncate" title={selection.context}>
                        {truncateText(selection.context, 50)}
                      </div>
                    {:else}
                      <span class="text-gray-400">-</span>
                    {/if}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDate(selection.created_at)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
{/if}
