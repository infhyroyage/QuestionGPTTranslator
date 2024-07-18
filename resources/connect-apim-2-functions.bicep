var apimBackendsName = 'backends-functions'
var apimName = 'qgtranslator-je-apim'
var apimNamedValuesNames = {
  functionsDefaultHostKey: 'named-values-functions-default-host-key'
}

var functionsName = 'qgtranslator-je-func'

var vaultName = 'qgtranslator-je-vault'
var vaultSecretNames = {
  functionsDefaultHostKey: 'functions-default-host-key'
}

// Key Vault
resource vaultSecretsFunctionsDefaultHostKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  name: '${vaultName}/${vaultSecretNames.functionsDefaultHostKey}'
  properties: {
    attributes: {
      enabled: true
    }
    value: listKeys(
      resourceId('Microsoft.Web/sites/host', functionsName, 'default'),
      '2022-09-01'
    ).functionKeys.default
  }
}

// API Management
resource apimNamedValuesFunctionsDefaultHostKey 'Microsoft.ApiManagement/service/namedValues@2022-08-01' = {
  name: '${apimName}/${apimNamedValuesNames.functionsDefaultHostKey}'
  properties: {
    displayName: apimNamedValuesNames.functionsDefaultHostKey
    keyVault: {
      secretIdentifier: vaultSecretsFunctionsDefaultHostKey.properties.secretUri
    }
    secret: true
  }
}
resource apimBackends 'Microsoft.ApiManagement/service/backends@2022-08-01' = {
  name: '${apimName}/${apimBackendsName}'
  properties: {
    description: functionsName
    url: 'https://${functionsName}.azurewebsites.net/api'
    protocol: 'http'
    resourceId: '${environment().resourceManager}${resourceId('Microsoft.Web/sites',functionsName)}'
    credentials: {
      header: {
        'x-functions-key': [
          '{{${apimNamedValuesNames.functionsDefaultHostKey}}}'
        ]
      }
    }
  }
  dependsOn: [apimNamedValuesFunctionsDefaultHostKey]
}
