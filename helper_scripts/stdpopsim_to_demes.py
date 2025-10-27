import stdpopsim
import demes
import demesdraw

# 1. Fetch the demography
species = "DroMel"
demography_name = "African3Epoch_1S16"

species = stdpopsim.get_species(species)
model = species.get_demographic_model(demography_name)


graph = model.model.to_demes()

demes.dump(graph, "DroMel_africa.yaml")
demesdraw.tubes(graph)
