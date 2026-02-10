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
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  },

  async getChatHistory(repositoryName: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/chat/history/${encodeURIComponent(repositoryName)}`, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  }
};

export const repoService = {
  async ingestRepo(repoUrl: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/ingest`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  },

  async getRepositories(token: string | null) {
    const response = await fetch(`${BASE_URL}/repositories`, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  },
  
  async deleteRepo(repoId: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/repositories/${repoId}`, {
      method: "DELETE",
      headers: await getAuthHeaders(token),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    if (response.status === 404) {
      throw new Error("Repository not found");
    }
    
    return response.json();
  }
};