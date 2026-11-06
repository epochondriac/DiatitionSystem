// Adds the saved login token to every request sent to our API, so plain fetch() calls are authenticated.
// On a 401 (expired/invalid token) the session is cleared and the user is sent to the login page.
export function installApiAuth() {
  const apiBase = import.meta.env.VITE_API_URL as string | undefined;
  if (!apiBase) return;
  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.startsWith(apiBase)) return originalFetch(input, init);

    const token = localStorage.getItem("auth_token");
    const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
    if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);

    const res = await originalFetch(input, { ...init, headers });
    const isLogin = url.includes("/api/auth/login");
    if (res.status === 401 && !isLogin && token) {
      localStorage.removeItem("auth_user");
      localStorage.removeItem("auth_token");
      window.location.assign("/login");
    }
    return res;
  };
}
