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
  
  if (!response.ok) {
    try {
      const errorData = await response.json();
      const detailMsg = errorData.detail || errorData.message || "Unknown error";
      throw new Error(`${response.status}: ${detailMsg}`);
    } catch (e) {
      if (e instanceof Error && e.message.includes(":")) {
        throw e; 
      }
      throw new Error(`Request failed with status ${response.status}`);
    }
  }
  
  return response.json();
}

export const chatService = {
  async sendMessage(message: string, token: string | null, repositoryName?: string) {
    const body: any = { 
      message,
      repository_name: repositoryName
    };
    
    const response = await fetch(`${BASE_URL}/api/chat`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify(body),
    });
    
    return handleResponse(response);
  },

  async getChatHistory(repositoryName: string, token: string | null) {
    const url = `${BASE_URL}/api/chat/history/${encodeURIComponent(repositoryName)}`;
    
    const response = await fetch(url, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  }
};

export const repoService = {
  async ingestRepo(repoUrl: string, token: string | null, orgId?: string | null) {
    const body: any = { 
      repo_url: repoUrl
    };
    
    if (orgId) {
      body.org_id = orgId;
    }
    
    const response = await fetch(`${BASE_URL}/api/ingest`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify(body),
    });
    
    return handleResponse(response);
  },

  async getRepositories(token: string | null, workspaceType: "personal" | "org" = "personal", orgId?: string | null) {
    const params = new URLSearchParams();
    params.append("workspace_type", workspaceType);
    
    if (orgId && workspaceType === "org") {
      params.append("org_id", orgId);
    }
    
    const queryString = params.toString();
    const url = `${BASE_URL}/api/repositories${queryString ? "?" + queryString : ""}`;
    
    const response = await fetch(url, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  },
  
  async deleteRepo(repoId: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/api/repositories/${repoId}`, {
      method: "DELETE",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  }
};

export const orgService = {
  async inviteMember(email: string, token: string | null, orgId?: string) {
    const response = await fetch(`${BASE_URL}/api/org/invite`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ email, org_id: orgId }),
    });
    
    return handleResponse(response);
  },

  async getOrgDetails(token: string | null, orgId?: string) {
    const params = new URLSearchParams();
    if (orgId) params.append("org_id", orgId);
    const queryString = params.toString();
    const url = `${BASE_URL}/api/org/details${queryString ? "?" + queryString : ""}`;
    
    const response = await fetch(url, {
      method: "GET",
      headers: await getAuthHeaders(token),
    });
    
    return handleResponse(response);
  },

  async leaveOrganization(orgId: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/api/org/leave`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ org_id: orgId }),
    });
    
    return handleResponse(response);
  }
};