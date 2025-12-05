# Synapse — Setup Local

Este projeto consiste em:

* **Back-end:** API em FastAPI com modelo RAG para analisar solicitações, gerar requisitos e criar cards no Jira.
* **Front-end:** Aplicação web em React.

Abaixo estão as instruções completas para executar ambos os ambientes localmente.

---

## 1. Pré-requisitos do Sistema

### Para o Back-end

1. **Python 3.11.x** (validado com 3.11.9)
2. **Git**
3. **(Opcional no Linux/macOS) libmagic** — utilizado pela lib `unstructured`

   * **Ubuntu/Debian:** `sudo apt-get install -y libmagic-dev`
   * **macOS:** `brew install libmagic`

### Para o Front-end

1. **Node.js + NPM**

   * Verifique se possui Node instalado:

     ```bash
     npm --version
     ```
   * Caso *não tenha*, instale pelo site oficial:
     [https://nodejs.org](https://nodejs.org) (versão LTS)

---

## 2. Clonar o Repositório

```bash
git clone https://github.com/ianjsm/Extensao-3-Synapse
cd Extensao-3-Synapse
```

---

## 3. Executar o Back-end (FastAPI)

Entre no diretório do back-end:

```bash
cd BACK-END
```

---

### **Passo 1: Configurar o `.env`**

1. Copie o arquivo de exemplo:

   ```bash
   # Windows
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```

2. Edite o arquivo `.env` com suas credenciais do Google e Jira.

---

### **Passo 2: Criar e Ativar Ambiente Virtual**

```bash
python -m venv venv

# Ativar no Windows
.\venv\Scripts\activate

# Ativar no macOS/Linux
# source venv/bin/activate
```

---

### **Passo 3: Instalar Dependências**

```bash
pip install -r requirements.txt
```

---

### **Passo 4: Rodar a Ingestão de Dados (OBRIGATÓRIO)**

Cria o banco vetorial usado pelo RAG.

```bash
python app/ingest.py
```

---

### **Passo 5: Iniciar a API**

```bash
python main.py
```

A API ficará disponível em:

```
http://127.0.0.1:8000
```

---

## 4. Executar o Front-end (React)

Volte para a raiz caso esteja no back-end:

```bash
cd ..
```

Entre na pasta do front-end:

```bash
cd FRONT-END
```

---

### **Passo 1: Verificar NPM**

```bash
npm --version
```

Se der erro → instale o Node.js conforme mostrado nos pré-requisitos.

---

### **Passo 2: Instalar Dependências**

```bash
npm install
```

---

### **Passo 3: Rodar o Servidor de Desenvolvimento**

```bash
npm run dev
```

Geralmente disponível em:

```
http://localhost:5173
```

---

## 5. Finalização

Após seguir os passos:

* **Back-end:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Front-end:** [http://localhost:5173](http://localhost:5173)
