import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent {
  features = [
    {
      title: 'Standalone Components',
      description: 'Using Angular 19 standalone components',
    },
    {
      title: 'Modern Angular',
      description: 'Built with the latest Angular features and best practices',
    },
    {
      title: 'Responsive Design',
      description: 'Fully responsive layout works on any device',
    },
  ];
}
