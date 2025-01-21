export { fetchWithCredentials };

export const fetchWithCredentials = (input: RequestInfo, init?: RequestInit): Promise<Response> => {
  const initWithCredentials = {
    ...init,
    credentials: 'include',
  };
  return fetch(input, initWithCredentials);
}; 