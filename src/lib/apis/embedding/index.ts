import {HATTO_LLM_API_BASE_URL} from '$lib/constants';

export const createNewIndex = async (name: string, category: string, geographic: string) => {
  let error = null;

  const res = await fetch(`${HATTO_LLM_API_BASE_URL}/embedding/index/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${localStorage.token}`
    },
    body: JSON.stringify({
      name, category, geographic
    })
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err.detail;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
};

export const getEmbeddingIndex = async () => {
  let error = null;

  const res = await fetch(`${HATTO_LLM_API_BASE_URL}/embedding/index/`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${localStorage.token}`
    },
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err.detail;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res.results;
};

export const getEmbeddedFiles = async (indexId: number) => {
  let error = null;

  const res = await fetch(`${HATTO_LLM_API_BASE_URL}/embedding/index/${indexId}/files`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${localStorage.token}`
    },
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err.detail;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res.results;
}

export const embeddingFile = async (indexId: number, file: File) => {
  let error = null;

  const formData = new FormData();
  formData.append('org_index_id', `${indexId}`);
  formData.append('files', file)

  const res = await fetch(`${HATTO_LLM_API_BASE_URL}/embedding/index-file`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      authorization: `Bearer ${localStorage.token}`
    },
    body: formData
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err.detail;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
}

export const queryRankedChunk = async (indexId: number, question: string) => {
  let error = null;

  const res = await fetch(`${HATTO_LLM_API_BASE_URL}/embedding/query-ranked-chunk`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      authorization: `Bearer ${localStorage.token}`
    },
    body: JSON.stringify({
      org_index_id: indexId, question
    })
  })
    .then(async (res) => {
      if (!res.ok) throw await res.json();
      return res.json();
    })
    .catch((err) => {
      error = err.detail;
      console.log(err);
      return null;
    });

  if (error) {
    throw error;
  }

  return res;
}