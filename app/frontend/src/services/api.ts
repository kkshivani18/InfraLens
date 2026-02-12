const BASE_URL = import.meta.env.VITE_API_URL;

async function getAuthHeaders(token: string | null): Promise<HeadersInit> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  return headers;
}

async function handleResponse(response: Response) {
  if (response.status === 401) {
    throw new Error("Unauthorized: Please sign in again");
  }
  
  if (response.status === 404) {
    throw new Error("Resource not found");
  }
  
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  
  return response.json();
}

export const chatService = {
  async sendMessage(message: string, token: string | null, repositoryName?: string) {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ 
        message,
        repository_name: repositoryName 
      }),
    });
    
    return handleResponse(response);
  },

  async getChatHistory(repositoryName: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/chat/history/${encodeURIComponent(repositoryName)}`, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  }
};

export const repoService = {
  async ingestRepo(repoUrl: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/ingest`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    
    return handleResponse(response);
  },

  async getRepositories(token: string | null) {
    const response = await fetch(`${BASE_URL}/repositories`, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  },
  
  async deleteRepo(repoId: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/repositories/${repoId}`, {
      method: "DELETE",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  }
};