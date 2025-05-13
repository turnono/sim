include .env
export 

# Start the Firestore emulator in one terminal:
#   make firestore-emulator
# Then run the app in another terminal:
#   make dev
# Then run the frontend in another terminal:
#   make frontend-do

firestore-emulator:
	@echo "[Firestore Emulator] Starting Firestore emulator. Run this in its own terminal window!"
	FIRESTORE_EMULATOR_HOST=localhost:8087 firebase emulators:start --only firestore,auth --project ${GOOGLE_CLOUD_PROJECT}

dev:
	@echo "[Dev Server] Starting ADK API server. Run this in a separate terminal after the emulator is running!"
	FIRESTORE_EMULATOR_HOST=localhost:8087 adk api_server --allow_origins="http://localhost:4200"

frontend-do:
	cd frontend && npm start


ngrok:
	@echo "[ngrok] Launching tunnel to smart-earwig-completely.ngrok-free.app:8000. Run this in its own terminal!"
	ngrok http --url=smart-earwig-completely.ngrok-free.app 8000
	


# production build and deploy

deploy-frontend:
	cd frontend && ng build --configuration=production && firebase deploy --only hosting:tjr-scheduler --project=${GOOGLE_CLOUD_PROJECT}

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
BOOKING_CALENDAR_ID=${BOOKING_CALENDAR_ID},\
ENV=${ENV},\
BOOKING_TIMEZONE=${BOOKING_TIMEZONE},\
DEPLOYED_CLOUD_SERVICE_URL=${DEPLOYED_CLOUD_SERVICE_URL}"

# Delete the agent service from Google Cloud Run
delete:
	gcloud run services delete ${AGENT_SERVICE_NAME} \
	--region ${GOOGLE_CLOUD_LOCATION}