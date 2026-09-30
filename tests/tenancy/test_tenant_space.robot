*** Settings ***
Documentation    Project and Namespace Resource Limit Test Cases
...    Verifies the creation of a project, a namespace within that project,
...    and validates that the applied resource limits/quotas (CPU and Memory)
...    are successfully applied and reflected in the API.
Test Tags        projects    namespaces    regression

Resource    ../../keywords/variables.resource
Resource    ../../keywords/common.resource

Resource    ../../keywords/project.resource
Resource    ../../keywords/namespace.resource

Suite Setup       Local Suite Setup
Suite Teardown    Local Suite Teardown
Test Teardown     Common Test Teardown


*** Variables ***
# Dynamic Variables
${PROJECT_NAME}      ${EMPTY}
${NAMESPACE_NAME}    ${EMPTY}

# Resource Limit Configuration
${CPU_LIMIT}         4
${MEMORY_LIMIT}      8Gi


*** Test Cases ***
Create Project And Namespace With Resource Limits
    [Tags]    p0
    [Documentation]    Creates a project and a namespace with specific resource limits,
    ...    then validates that both entities are successfully created and 
    ...    the resource limits are correctly applied at the Kubernetes/API level.
    
    # Create and validate the Project
    Project is created with resource limits    ${PROJECT_NAME}    cpu_limit=${CPU_LIMIT}    memory_limit=${MEMORY_LIMIT}
    Project should exist    ${PROJECT_NAME}
    Project should be active    ${PROJECT_NAME}
    
    # Create and validate the Namespace within the Project
    Namespace is created in project    ${NAMESPACE_NAME}    ${PROJECT_NAME}    cpu_limit=${CPU_LIMIT}    memory_limit=${MEMORY_LIMIT}
    Namespace should exist    ${NAMESPACE_NAME}
    Namespace should be active    ${NAMESPACE_NAME}

    # Validate limits are applied correctly
    ${actual_proj_cpu}    ${actual_proj_mem}=    Get Project Resource Limits    ${PROJECT_NAME}
    Should Be Equal As Strings    ${actual_proj_cpu}    ${CPU_LIMIT}
    ...    msg=Expected Project CPU limit ${CPU_LIMIT}, but got ${actual_proj_cpu}
    Should Be Equal As Strings    ${actual_proj_mem}    ${MEMORY_LIMIT}
    ...    msg=Expected Project Memory limit ${MEMORY_LIMIT}, but got ${actual_proj_mem}

    ${actual_ns_cpu}    ${actual_ns_mem}=    Get Namespace Resource Limits    ${NAMESPACE_NAME}
    Should Be Equal As Strings    ${actual_ns_cpu}    ${CPU_LIMIT}
    ...    msg=Expected Namespace CPU limit ${CPU_LIMIT}, but got ${actual_ns_cpu}
    Should Be Equal As Strings    ${actual_ns_mem}    ${MEMORY_LIMIT}
    ...    msg=Expected Namespace Memory limit ${MEMORY_LIMIT}, but got ${actual_ns_mem}


*** Keywords ***
Local Suite Setup
    ${suffix}=    Generate Unique Name
    Set Suite Variable    ${PROJECT_NAME}      project-${suffix}
    Set Suite Variable    ${NAMESPACE_NAME}    ns-${suffix}
    Set up test environment

Local Suite Teardown
    Run Keyword If All Tests Passed    Delete Suite Resources
    Run Keyword If Any Tests Failed    Log Variables

Delete Suite Resources
    # Delete the namespace first, then the project to avoid orphan resources
    Run Keyword And Ignore Error    Namespace is deleted    ${NAMESPACE_NAME}
    Run Keyword And Ignore Error    Project is deleted    ${PROJECT_NAME}