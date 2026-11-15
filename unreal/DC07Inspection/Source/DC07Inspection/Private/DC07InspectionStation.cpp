#include "DC07InspectionStation.h"

#include "Components/InputComponent.h"
#include "Components/MeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/EngineTypes.h"
#include "Engine/HitResult.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "Materials/MaterialInterface.h"
#include "MovieSceneSequencePlayer.h"

void ADC07InspectionStation::BeginPlay()
{
    Super::BeginPlay();
    APlayerController* Player = UGameplayStatics::GetPlayerController(this, 0);
    if (!Player)
    {
        return;
    }

    EnableInput(Player);
    Player->bShowMouseCursor = true;
    Player->SetInputMode(FInputModeGameAndUI());
    if (InspectionCamera)
    {
        Player->SetViewTarget(InspectionCamera.Get());
    }
    if (InputComponent)
    {
        InputComponent->BindKey(EKeys::LeftMouseButton, IE_Pressed, this,
            &ADC07InspectionStation::InspectAtCursor);
        InputComponent->BindKey(EKeys::M, IE_Pressed, this,
            &ADC07InspectionStation::PlayMaintenance);
    }
    Display(TEXT("DC-07 | Click equipment to inspect. Press M to play maintenance."));
}

void ADC07InspectionStation::EndPlay(const EEndPlayReason::Type Reason)
{
    ClearHighlight();
    Super::EndPlay(Reason);
}

void ADC07InspectionStation::InspectAtCursor()
{
    ClearHighlight();
    const APlayerController* Player = UGameplayStatics::GetPlayerController(this, 0);
    FHitResult Hit;
    if (!Player || !Player->GetHitResultUnderCursorByChannel(
        UEngineTypes::ConvertToTraceType(ECC_Visibility), true, Hit))
    {
        return;
    }

    for (const AActor* Actor = Hit.GetActor(); Actor; Actor = Actor->GetAttachParentActor())
    {
        const FDC07Equipment* Item = Equipment.FindByPredicate(
            [Actor](const FDC07Equipment& Candidate) { return Candidate.Target.Get() == Actor; });
        if (Item)
        {
            Highlight(*Item);
            Display(FString::Printf(TEXT("%s | %s"), *Item->Name.ToString(), *Item->Function.ToString()));
            if (Item->bPlaySequenceOnClick)
            {
                PlayMaintenance();
            }
            return;
        }
    }
}

void ADC07InspectionStation::Highlight(const FDC07Equipment& Item)
{
    if (!HighlightMaterial)
    {
        return;
    }

    TSet<AActor*> Actors;
    Actors.Add(Item.Target.Get());
    for (const TObjectPtr<AActor>& Connection : Item.Connections)
    {
        Actors.Add(Connection.Get());
    }

    TSet<UMeshComponent*> Meshes;
    for (AActor* Actor : Actors)
    {
        if (!IsValid(Actor))
        {
            continue;
        }
        TArray<UMeshComponent*> Components;
        Actor->GetComponents<UMeshComponent>(Components);
        for (UMeshComponent* Mesh : Components)
        {
            Meshes.Add(Mesh);
        }
    }
    for (UMeshComponent* Mesh : Meshes)
    {
        for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot)
        {
            UMaterialInterface* Original = Mesh->GetMaterial(Slot);
            RetainedMaterials.Add(Original);
            Originals.Add({Mesh, Slot, Original});
            Mesh->SetMaterial(Slot, HighlightMaterial.Get());
        }
    }
}

void ADC07InspectionStation::ClearHighlight()
{
    for (const FOriginalMaterial& Original : Originals)
    {
        if (UMeshComponent* Mesh = Original.Component.Get())
        {
            Mesh->SetMaterial(Original.Slot, Original.Material.Get());
        }
    }
    Originals.Reset();
    RetainedMaterials.Reset();
}

void ADC07InspectionStation::PlayMaintenance()
{
    ULevelSequencePlayer* SequencePlayer = MaintenanceSequence
        ? MaintenanceSequence->GetSequencePlayer() : nullptr;
    if (!SequencePlayer)
    {
        Display(TEXT("Assign the DC-07 maintenance Level Sequence actor."));
        return;
    }
    if (!SequencePlayer->IsPlaying())
    {
        SequencePlayer->SetPlaybackPosition(
            FMovieSceneSequencePlaybackParams(0.0f, EUpdatePositionMethod::Jump));
        SequencePlayer->Play();
    }
}

void ADC07InspectionStation::Display(const FString& Message) const
{
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(GetUniqueID(), 6.0f, FColor::Cyan, Message);
    }
}
