include .env
export 

firestore-emulator:
	@echo "[Firestore Emulator] Starting Firestore emulator. Run this in its own terminal window!"
	FIRESTORE_EMULATOR_HOST=localhost:8087 firebase emulators:start --only firestore,auth --project ${GOOGLE_CLOUD_PROJECT}

dev:
	@echo "[Dev Server] Starting ADK API server. Run this in a separate terminal after the emulator is running!"
	FIRESTORE_EMULATOR_HOST=localhost:8087 python main.py --allow_origins="http://localhost:4200"

frontend-do:
	cd frontend && npm start

# production build and deploy

deploy-frontend:
	cd frontend && ng build --configuration=production && firebase deploy --only hosting:tjr-sim-guide --project=${GOOGLE_CLOUD_PROJECT}

# Deploy the agent service to Google Cloud Run
deploy:
	gcloud run deploy ${AGENT_SERVICE_NAME} \
	--source . \
	--region ${GOOGLE_CLOUD_LOCATION} \
	--project ${GOOGLE_CLOUD_PROJECT} \
	--allow-unauthenticated \
	--port 8080 \
	--service-account ${AGENT_SERVICE_ACCOUNT} \
	--set-env-vars="GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},\
GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},\
GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI},\
GOOGLE_API_KEY=${GOOGLE_API_KEY},\
ENV=${ENV},\
DEPLOYED_CLOUD_SERVICE_URL=${DEPLOYED_CLOUD_SERVICE_URL}"

# Delete the agent service from Google Cloud Run
delete:
	gcloud run services delete ${AGENT_SERVICE_NAME} \
	--region ${GOOGLE_CLOUD_LOCATION}