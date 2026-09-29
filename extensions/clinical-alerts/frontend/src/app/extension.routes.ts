import { Routes } from '@angular/router';
import { ListAlertTriageComponent } from './list/list-alert-triage.component';
import { AddAlertTriageComponent } from './add/add-alert-triage.component';
import { ViewAlertTriageComponent } from './view/view-alert-triage.component';

// What the host lazy-loads (manifest frontend.remote.exposedModule = './Extension').
// THE EXPORTED CONST MUST BE NAMED `Extension`. No edit route: a triage is a point-in-time run.
export const Extension: Routes = [
  { path: '', component: ListAlertTriageComponent },
  { path: 'add', component: AddAlertTriageComponent },
  { path: 'view/:id', component: ViewAlertTriageComponent },
];
