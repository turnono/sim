// This file can be replaced during build by using the `fileReplacements` array.
// `ng build` replaces `environment.ts` with `environment.prod.ts`.

export const environment = {
  production: false,
  ownerFullName: 'Abdullah Abrahams',
  apiUrl: {
    agentService: 'http://localhost:8000', // Local development API
  },
  firebase: {
    projectId: 'taajirah',
    appId: '1:855515190257:web:2c01b97a96acc83556ea50',
    databaseURL:
      'https://taajirah-default-rtdb.europe-west1.firebasedatabase.app',
    storageBucket: 'taajirah.appspot.com',
    apiKey: 'AIzaSyDGaH72jq3Ev-Jue-5qm72OzpRCWzQMh9U',
    authDomain: 'taajirah.firebaseapp.com',
    messagingSenderId: '855515190257',
    measurementId: 'G-SP3FWBJNT3',
  },
};
