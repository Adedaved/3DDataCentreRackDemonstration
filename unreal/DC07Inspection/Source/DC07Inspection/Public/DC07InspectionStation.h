#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DC07InspectionStation.generated.h"

class ALevelSequenceActor;
class UMaterialInterface;
class UMeshComponent;

USTRUCT(BlueprintType)
struct DC07INSPECTION_API FDC07Equipment
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, Category="Equipment")
    TObjectPtr<AActor> Target;

    UPROPERTY(EditAnywhere, Category="Equipment")
    FText Name;

    UPROPERTY(EditAnywhere, Category="Equipment", meta=(MultiLine=true))
    FText Function;

    UPROPERTY(EditAnywhere, Category="Equipment")
    TArray<TObjectPtr<AActor>> Connections;

    UPROPERTY(EditAnywhere, Category="Equipment")
    bool bPlaySequenceOnClick = false;
};

UCLASS()
class DC07INSPECTION_API ADC07InspectionStation : public AActor
{
    GENERATED_BODY()

public:
    UPROPERTY(EditInstanceOnly, Category="Rack Inspection")
    TArray<FDC07Equipment> Equipment;

    UPROPERTY(EditInstanceOnly, Category="Rack Inspection")
    TObjectPtr<ALevelSequenceActor> MaintenanceSequence;

    UPROPERTY(EditAnywhere, Category="Rack Inspection")
    TObjectPtr<UMaterialInterface> HighlightMaterial;

    UPROPERTY(EditInstanceOnly, Category="Rack Inspection")
    TObjectPtr<AActor> InspectionCamera;

    UFUNCTION(BlueprintCallable, Category="Rack Inspection")
    void InspectAtCursor();

    UFUNCTION(BlueprintCallable, Category="Rack Inspection")
    void PlayMaintenance();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    struct FOriginalMaterial
    {
        TWeakObjectPtr<UMeshComponent> Component;
        int32 Slot = 0;
        TWeakObjectPtr<UMaterialInterface> Material;
    };

    void Highlight(const FDC07Equipment& Item);
    void ClearHighlight();
    void Display(const FString& Message) const;

    TArray<FOriginalMaterial> Originals;

    // Retain dynamic originals while they are temporarily off the mesh.
    UPROPERTY(Transient)
    TArray<TObjectPtr<UMaterialInterface>> RetainedMaterials;
};
