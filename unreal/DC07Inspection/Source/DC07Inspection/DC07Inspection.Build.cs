using UnrealBuildTool;

public class DC07Inspection : ModuleRules
{
    public DC07Inspection(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "InputCore", "LevelSequence", "MovieScene" });
    }
}
