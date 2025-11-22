param functionsName string
param storageName string

var storageBlobDataOwnerRoleDefinitionName = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var storageQueueDataContributorRoleDefinitionName = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributorRoleDefinitionName = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'

// Storage Account
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}

// Functions
resource functions 'Microsoft.Web/sites@2023-12-01' existing = {
  name: functionsName
}

// Role Assignments(Storage Blob Data Owner)
resource storageBlobDataOwnerRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: storageBlobDataOwnerRoleDefinitionName
}
resource functionsStorageBlobDataOwnerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functions.id, storageBlobDataOwnerRoleDefinition.id)
  properties: {
    roleDefinitionId: storageBlobDataOwnerRoleDefinition.id
    principalId: functions.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role Assignments(Storage Queue Data Contributor)
resource storageQueueDataContributorRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: storageQueueDataContributorRoleDefinitionName
}
resource functionsStorageQueueDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functions.id, storageQueueDataContributorRoleDefinition.id)
  properties: {
    roleDefinitionId: storageQueueDataContributorRoleDefinition.id
    principalId: functions.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role Assignments(Storage Table Data Contributor)
resource storageTableDataContributorRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: storageTableDataContributorRoleDefinitionName
}
resource functionsStorageTableDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, functions.id, storageTableDataContributorRoleDefinition.id)
  properties: {
    roleDefinitionId: storageTableDataContributorRoleDefinition.id
    principalId: functions.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
