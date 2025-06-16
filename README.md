# Talk to My UseCase

**Talk to My UseCase** delivers a seamless conversational experience for exploring and analyzing specific business use cases. This intelligent agent helps you understand, validate, and optimize your business scenarios through interactive dialogue, providing tailored insights and recommendations based on your specific requirements.

This intuitive experience is designed for **business analysts, product managers, and decision makers** who need to quickly evaluate use cases, understand their implications, and make data-driven decisions.

> [!WARNING]
> Application templates are intended to be starting points that provide guidance on how to develop, serve, and maintain AI applications.
> They require a developer or data scientist to adapt and modify them for their business requirements before being put into production.

## Table of contents
1. [Setup](#setup)
2. [Architecture overview](#architecture-overview)
3. [Why build AI Apps with DataRobot app templates?](#why-build-ai-apps-with-datarobot-app-templates)
4. [Data privacy](#data-privacy)
5. [Make changes](#make-changes)
   - [Change the frontend](#change-the-frontend)
   - [Change the LLM](#change-the-llm)
   - [Customize use case templates](#customize-use-case-templates)
6. [Tools](#tools)
7. [Share results](#share-results)
8. [Delete all provisioned resources](#delete-all-provisioned-resources)
9. [Setup for advanced users](#setup-for-advanced-users)

## Setup

Before proceeding, ensure you have access to the required credentials and services. This template is pre-configured to use an Azure OpenAI endpoint and Snowflake Database credentials. To run the template as-is, you will need access to Azure OpenAI (leverages `gpt-4o` by default). 

Codespace users can **skip steps 1 and 2**. For local development, follow all of the following steps.

1. If `pulumi` is not already installed, install the CLI following instructions [here](https://www.pulumi.com/docs/iac/download-install/).
   After installing for the first time, restart your terminal and run:
   ```bash
   pulumi login --local  # omit --local to use Pulumi Cloud (requires separate account)
   ```

2. Clone the template repository.

   ```bash
   git clone https://github.com/datarobot-community/talk-to-my-usecase-agent.git
   cd talk-to-my-usecase-agent
   ```

3. Rename the file `.env.template` to `.env` in the root directory of the repo and populate your credentials.

   ```bash
   DATAROBOT_API_TOKEN=...
   DATAROBOT_ENDPOINT=...  # e.g. https://app.datarobot.com/api/v2
   OPENAI_API_KEY=...
   OPENAI_API_VERSION=...  # e.g. 2024-02-01
   OPENAI_API_BASE=...  # e.g. https://your_org.openai.azure.com/
   OPENAI_API_DEPLOYMENT_ID=...  # e.g. gpt-4o
   PULUMI_CONFIG_PASSPHRASE=...  # Required. Choose your own alphanumeric passphrase to be used for encrypting pulumi config
   FRONTEND_TYPE=...  # Optional. Default is "streamlit". Set to "react" to use React frontend
   ```
   Use the following resources to locate the required credentials:
   - **DataRobot API Token**: Refer to the *Create a DataRobot API Key* section of the [DataRobot API Quickstart docs](https://docs.datarobot.com/en/docs/api/api-quickstart/index.html#create-a-datarobot-api-key).
   - **DataRobot Endpoint**: Refer to the *Retrieve the API Endpoint* section of the same [DataRobot API Quickstart docs](https://docs.datarobot.com/en/docs/api/api-quickstart/index.html#retrieve-the-api-endpoint).
   - **LLM Endpoint and API Key**: Refer to the [Azure OpenAI documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line%2Cjavascript-keyless%2Ctypescript-keyless%2Cpython-new&pivots=programming-language-python#retrieve-key-and-endpoint).

4. In a terminal, run:
   ```bash
   python quickstart.py YOUR_PROJECT_NAME  # Windows users may have to use `py` instead of `python`
   ```
   Python 3.10 - 12 are supported


Advanced users desiring control over virtual environment creation, dependency installation, environment variable setup
and `pulumi` invocation see [here](#setup-for-advanced-users).

## Architecture overview


App templates contain three families of complementary logic:

- **AI logic**: Necessary to service AI requests and produce predictions and completions.
  ```
  deployment_*/  # Chat agent model
  ```
- **App Logic**: Necessary for user consumption; whether via a hosted front-end or integrating into an external consumption layer.
  ```
  frontend/  # Streamlit frontend
  utils/  # App business logic & runtime helpers
  ```
- **Operational Logic**: Necessary to activate DataRobot assets.
  ```
  infra/__main__.py  # Pulumi program for configuring DataRobot to serve and monitor AI and app logic
  infra/  # Settings for resources and assets created in DataRobot
  ```

## Why build AI Apps with DataRobot app templates?

App Templates transform your AI projects from notebooks to production-ready applications. Too often, getting models into production means rewriting code, juggling credentials, and coordinating with multiple tools and teams just to make simple changes. DataRobot's composable AI apps framework eliminates these bottlenecks, letting you spend more time experimenting with your ML and app logic and less time wrestling with plumbing and deployment.
- Start building in minutes: Deploy complete AI applications instantly, then customize the AI logic or the front-end independently (no architectural rewrites needed).
- Keep working your way: Data scientists keep working in notebooks, developers in IDEs, and configs stay isolated. Update any piece without breaking others.
- Iterate with confidence: Make changes locally and deploy with confidence. Spend less time writing and troubleshooting plumbing and more time improving your app.

Each template provides an end-to-end AI architecture, from raw inputs to deployed application, while remaining highly customizable for specific business requirements.

## Data privacy
Your data privacy is important to us. Data handling is governed by the DataRobot [Privacy Policy](https://www.datarobot.com/privacy/), please review before using your own data with DataRobot.


## Make changes

### Change the frontend

The application uses Streamlit by default. To customize:

1. Run `pulumi up` to update your stack (Or rerun your quickstart)
   ```bash
   source set_env.sh  # On windows use `set_env.bat`
   pulumi up
   ```

### Change the LLM

1. Modify the `LLM` setting in `infra/settings_generative.py` by changing `LLM=LLMs.AZURE_OPENAI_GPT_4_O` to any other LLM from the `LLMs` object.
     - Trial users: Please set `LLM=LLMs.AZURE_OPENAI_GPT_4_O_MINI` since GPT-4o is not supported in the trial. Use the `OPENAI_API_DEPLOYMENT_ID` in `.env` to override which model is used in your azure organisation. You'll still see GPT 4o-mini in the playground, but the deployed app will use the provided azure deployment.
2. To use an existing TextGen model or deployment:
      - In `.env`: Set either the `TEXTGEN_REGISTERED_MODEL_ID` or the `TEXTGEN_DEPLOYMENT_ID`
      - In `.env`: Set `CHAT_MODEL_NAME` to the model name expected by the deployment (e.g. "claude-3-7-sonnet-20250219" for an anthropic deployment, "datarobot-deployed-llm" for NIM models ) 
      - (Optional) In `utils/api.py`: `ALTERNATIVE_LLM_BIG` and `ALTERNATIVE_LLM_SMALL` can be used for fine-grained control over which LLM is used for different tasks.
3. In `.env`: If not using an existing TextGen model or deployment, provide the required credentials dependent on your choice.
4. Run `pulumi up` to update your stack (Or rerun your quickstart).
      ```bash
      source set_env.sh  # On windows use `set_env.bat`
      pulumi up
      ```

> **⚠️ Availability information:**
> Using a NIM model requires custom model GPU inference, a premium feature. You will experience errors by using this type of model without the feature enabled. Contact your DataRobot representative or administrator for information on enabling this feature.

### Customize use case templates

#### Suggestion tools

- Modify CSV files in the `assets/` directory to customize available use case data
- Upload new or updated AI catalog data to change the available use cases and their parameters


#### modify prompts

- Edit `utils/prompts.py`

## Share results

1. Log into the DataRobot application.
2. Navigate to **Registry > Applications**.
3. Navigate to the application you want to share, open the actions menu, and select **Share** from the dropdown.

## Delete all provisioned resources

```bash
pulumi down
```

## Setup for advanced users
For manual control over the setup process adapt the following steps for MacOS/Linux to your environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source set_env.sh
pulumi stack init YOUR_PROJECT_NAME
pulumi up
```
e.g. for Windows/conda/cmd.exe this would be:
```bash
conda create --prefix .venv pip
conda activate .\.venv
pip install -r requirements.txt
set_env.bat
pulumi stack init YOUR_PROJECT_NAME
pulumi up
```
For projects that will be maintained, DataRobot recommends forking the repo so upstream fixes and improvements can be merged in the future.
